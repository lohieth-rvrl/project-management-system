from datetime import timedelta

from django.db.models import Count, F, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.projects.models import Project
from apps.risks.models import Risk
from apps.tasks.models import Sprint, Task
from apps.timesheets.models import TimeEntry


def _counts(qs, field):
    return {row[field]: row["n"] for row in qs.values(field).annotate(n=Count("id"))}


def _overdue_q():
    return Q(due_date__lt=timezone.localdate()) & ~Q(status="done")


@extend_schema(responses=OpenApiTypes.OBJECT)
class SearchView(APIView):
    """Quick search across projects, tasks, risks and people: /api/analytics/search/?q=text"""

    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if len(q) < 2:
            return Response({"query": q, "projects": [], "tasks": [], "risks": [], "people": []})
        projects = Project.objects.filter(Q(code__icontains=q) | Q(name__icontains=q))[:5]
        tasks = Task.objects.select_related("project").filter(
            Q(title__icontains=q) | Q(description__icontains=q))[:8]
        risks = Risk.objects.select_related("project").filter(title__icontains=q)[:5]
        people = User.objects.filter(is_active=True).filter(
            Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))[:5]
        return Response({
            "query": q,
            "projects": [{"id": p.id, "label": f"{p.code} - {p.name}", "sub": p.status} for p in projects],
            "tasks": [{"id": t.id, "project": t.project_id, "label": t.title,
                       "sub": f"{t.project.code} · {t.status}"} for t in tasks],
            "risks": [{"id": r.id, "project": r.project_id, "label": r.title,
                       "sub": f"{r.project.code} · score {r.score}"} for r in risks],
            "people": [{"id": u.id, "label": u.get_full_name() or u.username, "sub": u.role} for u in people],
        })


@extend_schema(responses=OpenApiTypes.OBJECT)
class OverviewView(APIView):
    """Organisation-wide snapshot for the main dashboard."""

    def get(self, request):
        tasks = Task.objects.all()
        total = tasks.count()
        done = tasks.filter(status="done").count()
        return Response({
            "projects_by_status": _counts(Project.objects.all(), "status"),
            "projects_by_health": _counts(Project.objects.exclude(status__in=["completed", "cancelled"]), "health"),
            "tasks_by_status": _counts(tasks, "status"),
            "tasks_by_priority": _counts(tasks.exclude(status="done"), "priority"),
            "total_tasks": total,
            "completion_rate": round(done / total * 100, 1) if total else 0,
            "overdue_tasks": tasks.filter(_overdue_q()).count(),
            "unassigned_open_tasks": tasks.filter(assignee__isnull=True).exclude(status="done").count(),
            "open_critical_risks": Risk.objects.filter(score__gte=15).exclude(status="closed").count(),
            "hours_last_7_days": float(
                TimeEntry.objects.filter(
                    work_date__gte=timezone.localdate() - timedelta(days=7)
                ).aggregate(h=Sum("hours"))["h"] or 0
            ),
        })


@extend_schema(responses=OpenApiTypes.OBJECT)
class ProjectSummaryView(APIView):
    """Progress, schedule and budget for one project."""

    def get(self, request, pk):
        return Response(project_summary(get_object_or_404(Project, pk=pk)))


def project_summary(project):
    tasks = project.tasks.all()
    total = tasks.count()
    done = tasks.filter(status="done").count()
    hours = TimeEntry.objects.filter(task__project=project).aggregate(h=Sum("hours"))["h"] or 0
    cost = float(hours) * float(project.hourly_rate)
    budget = float(project.budget)
    estimate = float(tasks.aggregate(e=Sum("estimate_hours"))["e"] or 0)
    return {
        "id": project.id,
        "code": project.code,
        "name": project.name,
        "status": project.status,
        "health": project.health,
        "total_tasks": total,
        "done_tasks": done,
        "progress_percent": round(done / total * 100, 1) if total else 0,
        "overdue_tasks": tasks.filter(_overdue_q()).count(),
        "tasks_by_status": _counts(tasks, "status"),
        "estimated_hours": estimate,
        "logged_hours": float(hours),
        "budget": budget,
        "cost_to_date": round(cost, 2),
        "budget_used_percent": round(cost / budget * 100, 1) if budget else None,
        "open_risks": project.risks.exclude(status="closed").count(),
        "milestones_pending": project.milestones.filter(status="pending").count(),
        "milestones_missed": project.milestones.filter(
            Q(status="missed") | Q(status="pending", due_date__lt=timezone.localdate())
        ).count(),
    }


@extend_schema(responses=OpenApiTypes.OBJECT)
class WorkloadView(APIView):
    """Open workload vs. capacity per person."""

    def get(self, request):
        week_start = timezone.localdate() - timedelta(days=7)
        rows = []
        for u in User.objects.filter(is_active=True).order_by("username"):
            open_tasks = Task.objects.filter(assignee=u).exclude(status="done")
            open_hours = float(open_tasks.aggregate(h=Sum("estimate_hours"))["h"] or 0)
            logged = float(TimeEntry.objects.filter(user=u, work_date__gte=week_start)
                           .aggregate(h=Sum("hours"))["h"] or 0)
            cap = float(u.weekly_capacity_hours)
            rows.append({
                "user": u.id,
                "username": u.username,
                "role": u.role,
                "open_tasks": open_tasks.count(),
                "overdue_tasks": open_tasks.filter(_overdue_q()).count(),
                "open_estimate_hours": open_hours,
                "logged_hours_7d": logged,
                "weekly_capacity": cap,
                "utilization_percent": round(logged / cap * 100, 1) if cap else 0,
                "overloaded": open_hours > cap * 2,
            })
        return Response(rows)


@extend_schema(responses=OpenApiTypes.OBJECT)
class VelocityView(APIView):
    """Story points completed per sprint."""

    def get(self, request):
        sprints = Sprint.objects.all().order_by("start_date")
        project = request.query_params.get("project")
        if project:
            sprints = sprints.filter(project_id=project)
        data = []
        for s in sprints:
            agg = s.tasks.aggregate(
                planned=Sum("story_points"),
                completed=Sum("story_points", filter=Q(status="done")),
            )
            data.append({
                "sprint": s.name,
                "project": s.project_id,
                "start_date": s.start_date,
                "end_date": s.end_date,
                "planned_points": agg["planned"] or 0,
                "completed_points": agg["completed"] or 0,
            })
        return Response(data)


@extend_schema(responses=OpenApiTypes.OBJECT)
class OverdueTasksView(APIView):
    def get(self, request):
        qs = (Task.objects.filter(_overdue_q())
              .select_related("project", "assignee").order_by("due_date")[:100])
        return Response([{
            "id": t.id, "title": t.title, "project": t.project.code,
            "assignee": t.assignee.username if t.assignee else None,
            "due_date": t.due_date, "priority": t.priority,
            "days_late": (timezone.localdate() - t.due_date).days,
        } for t in qs])


def _audited_models():
    from apps.accounts.models import User as UserModel
    from apps.projects.models import Milestone, ProjectMember
    from apps.timesheets.models import TimeEntry as TimeEntryModel

    return {"Task": Task, "Project": Project, "Sprint": Sprint, "Milestone": Milestone,
            "Member": ProjectMember, "Risk": Risk, "Timesheet": TimeEntryModel, "User": UserModel}


AUDIT_ACTIONS = {"created": "+", "updated": "~", "deleted": "-"}
AUDIT_MAX_DEPTH = 5000  # newest N changes are reachable; keeps the merge cheap


@extend_schema(responses=OpenApiTypes.OBJECT)
class AuditLogView(APIView):
    """Who changed what and when, across every tracked model, newest first.

    Paged like the rest of the API (?page=, ?page_size=) and filterable with
    ?entity=Task, ?action=created|updated|deleted and ?user=<username>.
    """

    def get(self, request):
        models = _audited_models()
        entity = request.query_params.get("entity")
        action = request.query_params.get("action")
        user = request.query_params.get("user")
        if entity and entity not in models:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"entity": f"Use one of: {', '.join(models)}"})
        if action and action not in AUDIT_ACTIONS:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"action": "Use created, updated or deleted"})

        def num(name, default, top):
            try:
                return max(1, min(int(request.query_params.get(name, default)), top))
            except ValueError:
                return default

        size = num("page_size", 25, 200)
        page = num("page", 1, 10 ** 6)
        need = min(page * size, AUDIT_MAX_DEPTH)

        total, entries = 0, []
        for label, model in models.items():
            if entity and label != entity:
                continue
            qs = model.history.all()
            if action:
                qs = qs.filter(history_type=AUDIT_ACTIONS[action])
            if user:
                qs = qs.filter(history_user__username=user)
            total += qs.count()
            for h in qs.select_related("history_user").order_by("-history_date")[:need]:
                name = (getattr(h, "title", None) or getattr(h, "name", None)
                        or getattr(h, "username", None) or f"{label} #{h.id}")
                entries.append({
                    "entity": label, "entity_id": h.id, "name": str(name),
                    "action": {"+": "created", "~": "updated", "-": "deleted"}[h.history_type],
                    "by": h.history_user.username if h.history_user else None,
                    "at": h.history_date,
                })
        entries.sort(key=lambda e: e["at"], reverse=True)
        offset = (page - 1) * size
        base = request.build_absolute_uri(request.path)
        def link(n):
            q = request.GET.copy()
            q["page"] = n
            return f"{base}?{q.urlencode()}"
        return Response({
            "count": total,
            "next": link(page + 1) if offset + size < min(total, AUDIT_MAX_DEPTH) else None,
            "previous": link(page - 1) if page > 1 else None,
            "results": entries[offset:offset + size],
        })


class ProjectReportView(APIView):
    """Download a project status report: /api/analytics/projects/<id>/report/?format=xlsx|pdf"""

    @extend_schema(responses=OpenApiTypes.BINARY)
    def get(self, request, pk):
        from django.http import HttpResponse
        from rest_framework.exceptions import ValidationError

        from . import reports

        project = get_object_or_404(Project, pk=pk)
        kind = request.query_params.get("file", request.query_params.get("format", "xlsx")).lower()
        if kind not in ("xlsx", "pdf"):
            raise ValidationError({"file": "Use xlsx or pdf"})
        data = reports.build_xlsx(project, project_summary(project)) if kind == "xlsx" \
            else reports.build_pdf(project, project_summary(project))
        ctype = ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if kind == "xlsx"
                 else "application/pdf")
        resp = HttpResponse(data, content_type=ctype)
        resp["Content-Disposition"] = f'attachment; filename="{project.code}-report.{kind}"'
        return resp


def _daterange(start, end):
    for i in range((end - start).days + 1):
        yield start + timedelta(days=i)


@extend_schema(responses=OpenApiTypes.OBJECT)
class BurndownView(APIView):
    """Work remaining per day against an ideal line. ?unit=tasks (default) or hours."""

    MAX_DAYS = 366

    def get(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        unit = "hours" if request.query_params.get("unit") == "hours" else "tasks"
        tasks = list(project.tasks.filter(parent__isnull=True))
        today = timezone.localdate()
        if not tasks:
            return Response({"unit": unit, "days": [], "remaining": [], "ideal": [], "scope": []})
        weight = (lambda t: float(t.estimate_hours)) if unit == "hours" else (lambda t: 1)
        first = min(t.created_at.date() for t in tasks)
        start = project.start_date or first
        end = max(project.end_date or today, today) if project.end_date else today
        start = max(start, end - timedelta(days=self.MAX_DAYS))
        days = list(_daterange(start, end))
        remaining, scope = [], []
        for d in days:
            existing = [t for t in tasks if t.created_at.date() <= d]
            open_ = [t for t in existing if not (t.completed_at and t.completed_at.date() <= d)]
            scope.append(round(sum(weight(t) for t in existing), 2))
            remaining.append(round(sum(weight(t) for t in open_), 2))
        planned_end = project.end_date or end
        total = scope[-1]
        span = max((planned_end - start).days, 1)
        ideal = [round(max(total * (1 - (d - start).days / span), 0), 2) for d in days]
        return Response({"unit": unit, "days": [d.isoformat() for d in days],
                         "remaining": remaining, "ideal": ideal, "scope": scope})


@extend_schema(responses=OpenApiTypes.OBJECT)
class BudgetTrendView(APIView):
    """Cumulative cost (logged hours x hourly rate) by week, against the budget."""

    def get(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        rate = float(project.hourly_rate)
        weekly = {}
        for e in TimeEntry.objects.filter(task__project=project).values("work_date", "hours"):
            monday = e["work_date"] - timedelta(days=e["work_date"].weekday())
            weekly[monday] = weekly.get(monday, 0) + float(e["hours"])
        weeks, cumulative, running = [], [], 0.0
        for monday in sorted(weekly):
            running += weekly[monday] * rate
            weeks.append(monday.isoformat())
            cumulative.append(round(running, 2))
        return Response({"weeks": weeks, "cumulative_cost": cumulative,
                         "weekly_hours": [round(weekly[m], 2) for m in sorted(weekly)],
                         "budget": float(project.budget)})
