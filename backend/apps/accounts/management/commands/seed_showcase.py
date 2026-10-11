"""Create one fully populated example project with its team, so every feature can be tried.

    SEED_SHOWCASE=1 SHOWCASE_PASSWORDS="anita:pw1,rahul:pw2,sneha:pw3,vikram:pw4,meena:pw5" \\
        python manage.py seed_showcase

Runs only when SEED_SHOWCASE=1, and does nothing if the SHOW project already exists, so it is safe on
every deploy. Passwords come from SHOWCASE_PASSWORDS (a user without one gets no working login).
Dates are relative to today so the timeline, burndown and overdue views look alive.
"""
import os
from datetime import datetime, time, timedelta, timezone as tz

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.notifications.models import Notification
from apps.notifications.services import notify
from apps.projects.models import Milestone, Project, ProjectMember
from apps.risks.models import Risk
from apps.tasks.models import Comment, Sprint, Task, TaskDependency
from apps.timesheets.models import TimeEntry

TEAM = [  # username, first, last, role, weekly capacity, project role
    ("anita", "Anita", "Sharma", "manager", 40, "Project Manager"),
    ("rahul", "Rahul", "Verma", "lead", 40, "Tech Lead"),
    ("sneha", "Sneha", "Iyer", "member", 40, "Frontend Developer"),
    ("vikram", "Vikram", "Nair", "member", 32, "Backend Developer"),
    ("meena", "Meena", "Das", "viewer", 20, "Client Stakeholder"),
]
CODE = "SHOW"


def stamp(d, hour=10):
    return datetime.combine(d, time(hour), tz.utc)


class Command(BaseCommand):
    help = "Create the SHOW example project with team, sprints, tasks, time, risks and notifications"

    def handle(self, *args, **opts):
        if os.environ.get("SEED_SHOWCASE") != "1":
            self.stdout.write("SEED_SHOWCASE is not 1: skipping showcase data")
            return
        if Project.objects.filter(code=CODE).exists():
            self.stdout.write("Showcase project already exists: nothing to do")
            return

        passwords = dict(p.split(":", 1) for p in os.environ.get("SHOWCASE_PASSWORDS", "").split(",") if ":" in p)
        today = timezone.localdate()
        d = lambda n: today + timedelta(days=n)  # noqa: E731
        u = {}
        for username, first, last, role, cap, _ in TEAM:
            user, created = User.objects.get_or_create(username=username, defaults={
                "first_name": first, "last_name": last, "role": role, "weekly_capacity_hours": cap})
            if created:
                if passwords.get(username):
                    user.set_password(passwords[username])
                else:
                    user.set_unusable_password()
                user.save()
            u[username] = user
        boss = u["anita"]

        def save(obj):
            obj._history_user = boss  # so the audit log shows a person, not "system"
            obj.save()
            return obj

        project = save(Project(
            code=CODE, name="Website Relaunch (example project)", status="active", health="amber",
            description="Example project that uses every feature: sprints, milestones, workflow rules, "
                        "dependencies, time tracking, risks, notifications and reports.",
            start_date=d(-28), end_date=d(35), budget=500000, hourly_rate=1500, owner=boss,
            done_requires_approval=True,
            workflow_transitions={"todo": ["in_progress", "blocked"], "in_progress": ["todo", "review", "blocked"],
                                  "review": ["in_progress", "done"], "blocked": ["in_progress"]}))
        for username, *_rest, prole in TEAM:
            ProjectMember.objects.create(project=project, user=u[username], role=prole,
                                         allocation_percent=100 if username != "vikram" else 80)

        s1 = save(Sprint(project=project, name="Sprint 1 - Foundations", goal="Design system and API skeleton",
                         start_date=d(-28), end_date=d(-15)))
        s2 = save(Sprint(project=project, name="Sprint 2 - Core pages", goal="Home, product and checkout pages",
                         start_date=d(-14), end_date=d(0)))
        s3 = save(Sprint(project=project, name="Sprint 3 - Launch prep", goal="Performance, QA and go-live",
                         start_date=d(1), end_date=d(14)))

        for name, due, status in [("Design approved", d(-20), "done"), ("Beta to client", d(7), "pending"),
                                  ("Content freeze", d(-3), "missed"), ("Go live", d(35), "pending")]:
            save(Milestone(project=project, name=name, due_date=due, status=status))

        # title, sprint, status, priority, assignee, points, est hours, start, due, created, completed
        rows = [
            ("Design system and style guide", s1, "done", "high", "sneha", 8, 24, -28, -20, -28, -21),
            ("Set up API skeleton and CI", s1, "done", "high", "vikram", 5, 16, -27, -22, -28, -22),
            ("Database schema for products", s1, "done", "medium", "vikram", 5, 12, -24, -18, -27, -18),
            ("Home page build", s2, "done", "high", "sneha", 8, 20, -14, -8, -15, -7),
            ("Product listing API", s2, "review", "high", "vikram", 8, 18, -12, -2, -14, None),
            ("Product page build", s2, "in_progress", "high", "sneha", 8, 22, -9, 1, -13, None),
            ("Checkout flow", s2, "blocked", "critical", "rahul", 13, 30, -8, -1, -13, None),
            ("Payment gateway integration", s2, "todo", "critical", "vikram", 13, 28, -2, 5, -13, None),
            ("Search with filters", s3, "todo", "medium", "sneha", 8, 16, 2, 9, -10, None),
            ("Load testing and tuning", s3, "todo", "medium", "rahul", 5, 10, 8, 12, -9, None),
            ("Accessibility audit", s3, "todo", "low", None, 3, 8, 9, 13, -6, None),
            ("Go-live checklist", s3, "todo", "high", "anita", 3, 6, 12, 14, -5, None),
        ]
        t = {}
        for title, sp, status, prio, who, pts, est, st, due, created, done in rows:
            task = Task(project=project, sprint=sp, title=title, status=status, priority=prio,
                        assignee=u.get(who), reporter=boss, story_points=pts, estimate_hours=est,
                        start_date=d(st), due_date=d(due),
                        description=f"{title}. Part of the {sp.name} scope.")
            save(task)
            Task.objects.filter(pk=task.pk).update(created_at=stamp(d(created)),
                                                  completed_at=stamp(d(done)) if done is not None else None)
            t[title] = task
        # subtasks and dependencies
        for sub, who in [("Wire up cart totals", "rahul"), ("Address form validation", "sneha"), ("Order confirmation email", "vikram")]:
            save(Task(project=project, parent=t["Checkout flow"], title=sub, status="todo", priority="medium",
                      assignee=u[who], reporter=boss, estimate_hours=4, due_date=d(3)))
        for task, needs in [("Checkout flow", "Product page build"), ("Payment gateway integration", "Checkout flow"),
                            ("Product page build", "Product listing API")]:
            TaskDependency.objects.create(task=t[task], depends_on=t[needs])

        # comments, with @mentions (these notify the person named)
        for title, author, body in [
            ("Checkout flow", "rahul", "Blocked on the payment sandbox keys. @anita can you chase the client?"),
            ("Checkout flow", "anita", "On it. @rahul I have asked for the keys by Friday."),
            ("Product listing API", "vikram", "Ready for review. @sneha the response format is in the docs."),
            ("Product page build", "sneha", "Using the new design tokens. Looks good on mobile."),
        ]:
            Comment.objects.create(task=t[title], author=u[author], body=body)

        # time entries over the last 4 weeks; older ones approved
        spread = {"sneha": ["Design system and style guide", "Home page build", "Product page build"],
                  "vikram": ["Set up API skeleton and CI", "Database schema for products", "Product listing API"],
                  "rahul": ["Checkout flow", "Set up API skeleton and CI"],
                  "anita": ["Go-live checklist"]}
        for who, titles in spread.items():
            for i in range(28):
                day = d(-27 + i)
                if day.weekday() >= 5 or day > today:
                    continue
                TimeEntry.objects.create(task=t[titles[i % len(titles)]], user=u[who], work_date=day,
                                         hours=[6, 7, 5, 8][i % 4] if who != "anita" else 2,
                                         note="Showcase entry", approved=day < d(-7), approved_by=boss if day < d(-7) else None)

        # risks (score = probability x impact; 15+ is critical)
        for title, prob, imp, status, owner, mit in [
            ("Payment provider approval may slip", 4, 5, "open", "anita", "Escalate through the client sponsor; prepare a fallback gateway."),
            ("Key developer availability in sprint 3", 3, 4, "mitigating", "rahul", "Cross-train a second developer on checkout."),
            ("Content from client arrives late", 4, 3, "open", "anita", "Agree a content deadline in writing."),
            ("Old browser support", 2, 2, "closed", "sneha", "Support policy agreed: last two versions."),
        ]:
            save(Risk(project=project, title=title, probability=prob, impact=imp, status=status, owner=u[owner], mitigation=mit))

        # a few notifications so the inbox is not empty (no email: showcase users have no address)
        link = lambda name: f"/tasks?task={t[name].id}"  # noqa: E731
        notify([u["sneha"]], Notification.Kind.ASSIGNED, "You were assigned: Search with filters", "SHOW - Medium priority", link("Search with filters"), actor=boss)
        notify([u["rahul"]], Notification.Kind.MENTION, "Anita mentioned you on: Checkout flow", "On it. @rahul I have asked for the keys by Friday.", link("Checkout flow"), actor=boss)
        notify([u["vikram"]], Notification.Kind.STATUS, "Product listing API: In Progress to In Review", "SHOW", link("Product listing API"), actor=boss)
        notify([boss], Notification.Kind.RISK, "Critical risk on SHOW: Payment provider approval may slip", "Probability 4 x impact 5 = 20", "/risks", actor=u["rahul"])
        notify([u["sneha"]], Notification.Kind.DUE, "Product page build is due tomorrow", "SHOW task assigned to you.", link("Product page build"))

        self.stdout.write(self.style.SUCCESS(f"Showcase project {CODE} created with {len(TEAM)} team members"))
