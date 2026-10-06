import pytest
from django.core import mail
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.notifications.models import Notification
from apps.projects.models import Project
from apps.tasks.models import Task

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def sync(settings):
    settings.NOTIFY_SYNC = True
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.NOTIFY_WEBHOOK_URL = "http://hook.invalid/x"


@pytest.fixture
def hooks(monkeypatch):
    sent = []
    monkeypatch.setattr("apps.notifications.services._post_webhook", lambda text: sent.append(text))
    return sent


def mk(name, role="member", **kw):
    return User.objects.create_user(username=name, password="x" * 10, role=role, email=f"{name}@x.com", **kw)


def cl(u):
    c = APIClient()
    c.force_authenticate(u)
    return c


@pytest.fixture
def world():
    boss, dev, qa = mk("boss", "manager"), mk("dev"), mk("qa")
    p = Project.objects.create(name="P", code="PX", owner=boss)
    return boss, dev, qa, p


def test_assign_notifies_assignee_with_email_not_self(world):
    boss, dev, qa, p = world
    cl(boss).post("/api/tasks/", {"project": p.id, "title": "T1", "assignee": dev.id})
    n = Notification.objects.get(user=dev)
    assert n.kind == "assigned" and "T1" in n.title
    assert len(mail.outbox) == 1 and mail.outbox[0].to == ["dev@x.com"]
    cl(boss).post("/api/tasks/", {"project": p.id, "title": "T2", "assignee": boss.id})
    assert not Notification.objects.filter(user=boss).exists()


def test_email_opt_out(world):
    boss, dev, qa, p = world
    dev.email_notifications = False
    dev.save()
    cl(boss).post("/api/tasks/", {"project": p.id, "title": "T", "assignee": dev.id})
    assert Notification.objects.filter(user=dev).count() == 1 and mail.outbox == []


def test_status_change_and_blocked_webhook(world, hooks):
    boss, dev, qa, p = world
    t = Task.objects.create(project=p, title="T", assignee=dev, reporter=boss)
    cl(dev).patch(f"/api/tasks/{t.id}/", {"status": "blocked"}, format="json")
    assert Notification.objects.filter(user=boss, kind="status").count() == 1
    assert len(hooks) == 1


def test_comment_and_mention(world):
    boss, dev, qa, p = world
    t = Task.objects.create(project=p, title="T", assignee=dev, reporter=boss)
    cl(boss).post("/api/comments/", {"task": t.id, "body": "ping @qa please"})
    assert Notification.objects.filter(user=qa, kind="mention").count() == 1
    assert Notification.objects.filter(user=dev, kind="comment").count() == 1
    assert not Notification.objects.filter(user=qa, kind="comment").exists()


def test_critical_risk_webhook(world, hooks):
    boss, dev, qa, p = world
    cl(dev).post("/api/risks/", {"project": p.id, "title": "R", "probability": 5, "impact": 4})
    assert Notification.objects.filter(user=boss, kind="risk").count() == 1 and len(hooks) == 1


def test_inbox_is_private_and_read_flow(world):
    boss, dev, qa, p = world
    cl(boss).post("/api/tasks/", {"project": p.id, "title": "T", "assignee": dev.id})
    assert cl(qa).get("/api/notifications/").data["count"] == 0
    assert cl(dev).get("/api/notifications/unread-count/").data["count"] == 1
    nid = cl(dev).get("/api/notifications/").data["results"][0]["id"]
    assert cl(qa).post(f"/api/notifications/{nid}/read/").status_code == 404
    assert cl(dev).post(f"/api/notifications/{nid}/read/").status_code == 200
    assert cl(dev).get("/api/notifications/unread-count/").data["count"] == 0


def test_mark_all_read(world):
    boss, dev, qa, p = world
    for i in range(3):
        cl(boss).post("/api/tasks/", {"project": p.id, "title": f"T{i}", "assignee": dev.id})
    cl(dev).post("/api/notifications/mark-all-read/")
    assert cl(dev).get("/api/notifications/?unread=1").data["count"] == 0


def test_due_reminders_once_a_day(world):
    from datetime import date
    from django.core.management import call_command
    boss, dev, qa, p = world
    Task.objects.create(project=p, title="Late", assignee=dev, due_date=date(2020, 1, 1))
    call_command("send_due_reminders")
    call_command("send_due_reminders")
    assert Notification.objects.filter(user=dev, kind="due").count() == 1


def test_me_patch_only_changes_email_preference(world):
    boss, dev, qa, p = world
    r = cl(dev).patch("/api/users/me/", {"email_notifications": False, "role": "admin"}, format="json")
    dev.refresh_from_db()
    assert r.status_code == 200 and dev.email_notifications is False and dev.role == "member"
