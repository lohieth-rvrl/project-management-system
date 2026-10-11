import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.notifications.models import Notification
from apps.projects.models import Project
from apps.risks.models import Risk
from apps.tasks.models import Task
from apps.timesheets.models import TimeEntry

pytestmark = pytest.mark.django_db
PW = "anita:Strong-Pass-1,rahul:Strong-Pass-2,sneha:Strong-Pass-3,vikram:Strong-Pass-4"


def test_skipped_unless_enabled(monkeypatch):
    monkeypatch.delenv("SEED_SHOWCASE", raising=False)
    call_command("seed_showcase")
    assert not Project.objects.exists()


def test_creates_everything_once_and_logins_work(monkeypatch):
    monkeypatch.setenv("SEED_SHOWCASE", "1")
    monkeypatch.setenv("SHOWCASE_PASSWORDS", PW)
    call_command("seed_showcase")
    call_command("seed_showcase")  # second run changes nothing
    p = Project.objects.get(code="SHOW")
    assert Project.objects.count() == 1 and p.members.count() == 5 and p.sprints.count() == 3
    assert p.milestones.count() == 4 and p.tasks.filter(parent__isnull=False).count() == 3
    assert {"todo", "in_progress", "review", "blocked", "done"} <= set(p.tasks.values_list("status", flat=True))
    assert Task.objects.filter(due_date__lt=__import__("datetime").date.today()).exclude(status="done").exists()  # overdue
    assert TimeEntry.objects.filter(approved=True).exists() and TimeEntry.objects.filter(approved=False).exists()
    assert Risk.objects.filter(score__gte=15).exists() and Notification.objects.exists()
    c = APIClient()
    assert c.post("/api/auth/token/", {"username": "anita", "password": "Strong-Pass-1"}).status_code == 200
    assert c.post("/api/auth/token/", {"username": "meena", "password": "anything"}).status_code == 401  # no password given
    assert User.objects.get(username="meena").role == "viewer"


def test_workflow_rules_apply_to_the_showcase(monkeypatch):
    monkeypatch.setenv("SEED_SHOWCASE", "1")
    monkeypatch.setenv("SHOWCASE_PASSWORDS", PW)
    call_command("seed_showcase")
    c = APIClient()
    c.force_authenticate(User.objects.get(username="sneha"))
    todo = Task.objects.filter(project__code="SHOW", status="todo", parent__isnull=True).first()
    assert c.patch(f"/api/tasks/{todo.id}/", {"status": "done"}, format="json").status_code == 400
    assert c.get(f"/api/analytics/projects/{todo.project_id}/burndown/").data["days"]


def test_ensure_admin_runs_showcase_when_enabled(monkeypatch):
    monkeypatch.setenv("DJANGO_SUPERUSER_USERNAME", "root")
    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "first-password-1")
    monkeypatch.setenv("SEED_SHOWCASE", "1")
    call_command("ensure_admin")
    assert Project.objects.filter(code="SHOW").exists()
