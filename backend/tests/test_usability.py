from datetime import date, timedelta

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.projects.models import Milestone, Project
from apps.tasks.models import Sprint, Task

pytestmark = pytest.mark.django_db


def mk(name, role="member", **kw):
    return User.objects.create_user(username=name, password="OldPass12345", role=role, **kw)


def client(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


# ---------- change password ----------

def test_change_password_success_and_old_stops_working():
    u = mk("pw")
    r = client(u).post("/api/users/change-password/", {"old_password": "OldPass12345", "new_password": "BrandNew-9876"})
    assert r.status_code == 200
    login = APIClient()
    assert login.post("/api/auth/token/", {"username": "pw", "password": "OldPass12345"}).status_code == 401
    assert login.post("/api/auth/token/", {"username": "pw", "password": "BrandNew-9876"}).status_code == 200


def test_change_password_wrong_old_password():
    r = client(mk("pw2")).post("/api/users/change-password/", {"old_password": "nope", "new_password": "BrandNew-9876"})
    assert r.status_code == 400 and "old_password" in r.data


@pytest.mark.parametrize("weak", ["short", "password", "12345678"])
def test_change_password_rejects_weak_new_password(weak):
    r = client(mk("pw3")).post("/api/users/change-password/", {"old_password": "OldPass12345", "new_password": weak})
    assert r.status_code == 400


def test_change_password_requires_login():
    assert APIClient().post("/api/users/change-password/", {}).status_code == 401


# ---------- user management guard rails ----------

def test_manager_cannot_grant_admin_role():
    boss = mk("boss", "manager")
    r = client(boss).post("/api/users/", {"username": "sneaky", "password": "LongEnough123", "role": "admin"})
    assert r.status_code == 400
    assert not User.objects.filter(username="sneaky").exists()


def test_admin_can_grant_admin_role():
    r = client(mk("root", "admin")).post("/api/users/", {"username": "second", "password": "LongEnough123", "role": "admin"})
    assert r.status_code == 201


def test_manager_cannot_edit_or_delete_admin():
    admin, boss = mk("a1", "admin"), mk("m1", "manager")
    assert client(boss).patch(f"/api/users/{admin.id}/", {"first_name": "x"}).status_code == 403
    assert client(boss).delete(f"/api/users/{admin.id}/").status_code == 403


def test_cannot_delete_self_or_deactivate_self():
    boss = mk("m2", "manager")
    c = client(boss)
    assert c.delete(f"/api/users/{boss.id}/").status_code == 400
    assert c.patch(f"/api/users/{boss.id}/", {"is_active": False}).status_code == 400
    assert c.patch(f"/api/users/{boss.id}/", {"role": "member"}).status_code == 400
    assert User.objects.filter(pk=boss.id, is_active=True, role="manager").exists()


def test_manager_can_deactivate_a_member():
    boss, m = mk("m3", "manager"), mk("worker")
    assert client(boss).patch(f"/api/users/{m.id}/", {"is_active": False}).status_code == 200
    m.refresh_from_db()
    assert m.is_active is False


# ---------- project / sprint / milestone edit + delete ----------

@pytest.fixture
def project():
    return Project.objects.create(code="ED", name="Editable")


def test_project_edit_and_delete_permissions(project):
    member, boss = mk("mem"), mk("mgr", "manager")
    assert client(member).patch(f"/api/projects/{project.id}/", {"name": "Renamed"}).status_code == 200
    assert client(member).delete(f"/api/projects/{project.id}/").status_code == 403
    assert client(boss).delete(f"/api/projects/{project.id}/").status_code == 204


def test_sprint_and_milestone_crud(project):
    c = client(mk("lead1", "lead"))
    s = c.post("/api/sprints/", {"project": project.id, "name": "S1", "start_date": "2026-10-01", "end_date": "2026-10-14"})
    assert s.status_code == 201
    assert c.patch(f"/api/sprints/{s.data['id']}/", {"goal": "Ship it"}).data["goal"] == "Ship it"
    bad = c.post("/api/sprints/", {"project": project.id, "name": "S2", "start_date": "2026-10-14", "end_date": "2026-10-01"})
    assert bad.status_code == 400
    m = c.post("/api/milestones/", {"project": project.id, "name": "Beta", "due_date": "2026-11-01"})
    assert m.status_code == 201
    assert c.patch(f"/api/milestones/{m.data['id']}/", {"status": "done"}).data["status"] == "done"
    assert client(mk("boss2", "manager")).delete(f"/api/milestones/{m.data['id']}/").status_code == 204


# ---------- task filters ----------

def test_task_filters_overdue_unassigned_and_dates(project):
    w = mk("filt")
    today = date.today()
    Task.objects.create(project=project, title="late", due_date=today - timedelta(days=2), assignee=w)
    Task.objects.create(project=project, title="late but done", due_date=today - timedelta(days=2), status="done")
    Task.objects.create(project=project, title="future", due_date=today + timedelta(days=9))
    c = client(w)
    titles = lambda q: sorted(t["title"] for t in c.get(f"/api/tasks/?{q}").data["results"])
    assert titles("overdue=true") == ["late"]
    assert titles("overdue=false") == ["future", "late but done"]
    assert titles("unassigned=true") == ["future", "late but done"]
    assert titles("unassigned=false") == ["late"]
    assert titles(f"due_before={today}") == ["late", "late but done"]
    assert titles(f"assignee={w.id}") == ["late"]
    assert titles("search=futu") == ["future"]


# ---------- search ----------

def test_search_finds_across_types_and_short_query_is_empty(project):
    u = mk("searcher", first_name="Zelda")
    Task.objects.create(project=project, title="Fix zebra crossing bug")
    c = client(u)
    r = c.get("/api/analytics/search/?q=zeb").data
    assert [t["label"] for t in r["tasks"]] == ["Fix zebra crossing bug"]
    assert c.get("/api/analytics/search/?q=zel").data["people"][0]["label"].startswith("Zelda")
    assert c.get("/api/analytics/search/?q=edit").data["projects"][0]["label"] == "ED - Editable"
    empty = c.get("/api/analytics/search/?q=z").data
    assert empty["tasks"] == [] and empty["projects"] == []


def test_search_requires_login():
    assert APIClient().get("/api/analytics/search/?q=abc").status_code == 401
