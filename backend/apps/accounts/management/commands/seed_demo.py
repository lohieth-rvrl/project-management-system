"""Seed demo data: python manage.py seed_demo"""
import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.projects.models import Milestone, Project, ProjectMember
from apps.risks.models import Risk
from apps.tasks.models import Sprint, Task
from apps.timesheets.models import TimeEntry

PEOPLE = [
    ("admin", "admin", "Admin"),
    ("meera", "manager", "Meera"),
    ("arun", "lead", "Arun"),
    ("priya", "member", "Priya"),
    ("karthik", "member", "Karthik"),
    ("divya", "viewer", "Divya"),
]


class Command(BaseCommand):
    help = "Create demo users, projects, tasks, time entries and risks"

    def handle(self, *args, **opts):
        random.seed(7)
        today = timezone.localdate()
        users = {}
        for username, role, first in PEOPLE:
            u, created = User.objects.get_or_create(
                username=username,
                defaults={"role": role, "first_name": first, "email": f"{username}@example.com",
                          "is_staff": role == "admin", "is_superuser": role == "admin"})
            if created:
                u.set_password("demo12345")
                u.save()
            users[username] = u
        workers = [users["arun"], users["priya"], users["karthik"]]

        specs = [
            ("ERP", "ERP Modernisation", "active", "amber", 250000, 60),
            ("MOB", "Customer Mobile App", "active", "green", 120000, 55),
            ("DWH", "Data Warehouse Migration", "planning", "green", 90000, 70),
        ]
        statuses = ["todo", "in_progress", "review", "blocked", "done", "done"]
        priorities = ["low", "medium", "high", "critical"]
        for code, name, status, health, budget, rate in specs:
            p, created = Project.objects.get_or_create(code=code, defaults=dict(
                name=name, status=status, health=health, budget=budget, hourly_rate=rate,
                owner=users["meera"], start_date=today - timedelta(days=45),
                end_date=today + timedelta(days=90)))
            if not created:
                continue
            for u in workers:
                ProjectMember.objects.create(project=p, user=u)
            Milestone.objects.create(project=p, name="Design sign-off",
                                     due_date=today - timedelta(days=10), status="done")
            Milestone.objects.create(project=p, name="Beta release",
                                     due_date=today + timedelta(days=30))
            sprint = Sprint.objects.create(project=p, name="Sprint 1",
                                           start_date=today - timedelta(days=14),
                                           end_date=today)
            for i in range(1, 13):
                st = random.choice(statuses)
                t = Task.objects.create(
                    project=p, sprint=sprint if i <= 8 else None,
                    title=f"{code}-{i}: {random.choice(['Build', 'Review', 'Test', 'Document', 'Deploy'])} component {i}",
                    status=st, priority=random.choice(priorities),
                    assignee=random.choice(workers), reporter=users["meera"],
                    estimate_hours=random.choice([4, 8, 16, 24]),
                    story_points=random.choice([1, 2, 3, 5, 8]),
                    due_date=today + timedelta(days=random.randint(-10, 30)),
                    completed_at=timezone.now() if st == "done" else None)
                if st in ("in_progress", "review", "done"):
                    for d in range(random.randint(1, 3)):
                        TimeEntry.objects.create(
                            task=t, user=t.assignee, work_date=today - timedelta(days=d + 1),
                            hours=random.choice([2, 3, 4, 6]), approved=random.random() > 0.5)
            Risk.objects.create(project=p, title="Key developer unavailable", probability=3,
                                impact=4, owner=users["meera"], mitigation="Cross-train a backup")
            Risk.objects.create(project=p, title="Scope creep from stakeholders", probability=4,
                                impact=4, owner=users["meera"], mitigation="Change control board")
        self.stdout.write(self.style.SUCCESS(
            "Demo data ready. Log in as meera / demo12345 (manager) or admin / demo12345"))
