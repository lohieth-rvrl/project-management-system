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
        project = get_object_or_404(Project, pk=pk)
        tasks = project.tasks.all()
        total = tasks.count()
        done = tasks.filter(status="done").count()
        hours = TimeEntry.objects.filter(task__project=project).aggregate(h=Sum("hours"))["h"] or 0
        cost = float(hours) * float(project.hourly_rate)
        budget = float(project.budget)
        estimate = float(tasks.aggregate(e=Sum("estimate_hours"))["e"] or 0)
        return Response({
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
        })


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


@extend_schema(responses=OpenApiTypes.OBJECT)
class AuditLogView(APIView):
    """Who changed what and when, merged across the main tracked models."""

    def get(self, request):
        limit = min(int(request.query_params.get("limit", 50)), 200)
        entries = []
        for model, label in ((Task, "Task"), (Project, "Project")):
            for h in model.history.select_related("history_user").order_by("-history_date")[:limit]:
                entries.append({
                    "entity": label,
                    "entity_id": h.id,
                    "name": getattr(h, "title", None) or getattr(h, "name", ""),
                    "action": {"+": "created", "~": "updated", "-": "deleted"}[h.history_type],
                    "by": h.history_user.username if h.history_user else None,
                    "at": h.history_date,
                })
        entries.sort(key=lambda e: e["at"], reverse=True)
        return Response(entries[:limit])
