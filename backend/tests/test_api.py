from datetime import date, timedelta

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.projects.models import Project
from apps.tasks.models import Sprint, Task

pytestmark = pytest.mark.django_db


def make_user(username, role="member"):
    return User.objects.create_user(username=username, password="pass12345", role=role,
                                    email=f"{username}@example.com")


def client_for(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


@pytest.fixture
def manager():
    return make_user("mgr", "manager")


@pytest.fixture
def member():
    return make_user("mem", "member")


@pytest.fixture
def viewer():
    return make_user("view", "viewer")


@pytest.fixture
def project(manager):
    return Project.objects.create(code="PMS", name="PMS", owner=manager, budget=10000,
                                  hourly_rate=50)


def test_jwt_login_and_me():
    make_user("alice")
    c = APIClient()
    r = c.post("/api/auth/token/", {"username": "alice", "password": "pass12345"})
    assert r.status_code == 200
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
    assert c.get("/api/users/me/").data["username"] == "alice"


def test_unauthenticated_blocked():
    assert APIClient().get("/api/projects/").status_code == 401


def test_viewer_cannot_write_but_can_read(viewer, project):
    c = client_for(viewer)
    assert c.get("/api/projects/").status_code == 200
    r = c.post("/api/projects/", {"code": "X", "name": "X"})
    assert r.status_code == 403


def test_member_cannot_delete_manager_can(member, manager, project):
    assert client_for(member).delete(f"/api/projects/{project.id}/").status_code == 403
    assert client_for(manager).delete(f"/api/projects/{project.id}/").status_code == 204


def test_only_manager_can_create_users(member, manager):
    payload = {"username": "new", "password": "longenough1", "role": "member"}
    assert client_for(member).post("/api/users/", payload).status_code == 403
    assert client_for(manager).post("/api/users/", payload).status_code == 201


def test_project_date_validation(manager):
    r = client_for(manager).post("/api/projects/", {
        "code": "D1", "name": "Bad dates",
        "start_date": "2026-05-10", "end_date": "2026-05-01"})
    assert r.status_code == 400


def test_task_completed_at_set_and_cleared(member, project):
    c = client_for(member)
    r = c.post("/api/tasks/", {"project": project.id, "title": "T"})
    assert r.status_code == 201
    tid = r.data["id"]
    assert c.patch(f"/api/tasks/{tid}/", {"status": "done"}).data["completed_at"] is not None
    assert c.patch(f"/api/tasks/{tid}/", {"status": "todo"}).data["completed_at"] is None


def test_reporter_set_from_request(member, project):
    r = client_for(member).post("/api/tasks/", {"project": project.id, "title": "T"})
    assert r.data["reporter"] == member.id


def test_subtask_must_share_project(member, manager, project):
    other = Project.objects.create(code="OTH", name="Other", owner=manager)
    parent = Task.objects.create(project=other, title="p")
    r = client_for(member).post("/api/tasks/", {"project": project.id, "title": "c",
                                                "parent": parent.id})
    assert r.status_code == 400


def test_dependency_rejects_self_and_cycle(member, project):
    a = Task.objects.create(project=project, title="a")
    b = Task.objects.create(project=project, title="b")
    c = client_for(member)
    assert c.post("/api/task-dependencies/", {"task": a.id, "depends_on": a.id}).status_code == 400
    assert c.post("/api/task-dependencies/", {"task": a.id, "depends_on": b.id}).status_code == 201
    assert c.post("/api/task-dependencies/", {"task": b.id, "depends_on": a.id}).status_code == 400


def test_time_entry_flow_and_approval(member, manager, project):
    t = Task.objects.create(project=project, title="t", assignee=member)
    mc = client_for(member)
    r = mc.post("/api/time-entries/", {"task": t.id, "work_date": "2026-10-01", "hours": "4.5"})
    assert r.status_code == 201
    eid = r.data["id"]
    assert r.data["user"] == member.id
    assert mc.post("/api/time-entries/", {"task": t.id, "work_date": "2026-10-01",
                                          "hours": "30"}).status_code == 400
    assert mc.post(f"/api/time-entries/{eid}/approve/").status_code == 403
    assert client_for(manager).post(f"/api/time-entries/{eid}/approve/").status_code == 200
    assert mc.patch(f"/api/time-entries/{eid}/", {"hours": "1"}).status_code == 403


def test_member_only_sees_own_time(member, manager, project):
    t = Task.objects.create(project=project, title="t")
    client_for(member).post("/api/time-entries/", {"task": t.id, "work_date": "2026-10-01", "hours": "1"})
    client_for(manager).post("/api/time-entries/", {"task": t.id, "work_date": "2026-10-01", "hours": "2"})
    assert client_for(member).get("/api/time-entries/").data["count"] == 1
    assert client_for(manager).get("/api/time-entries/").data["count"] == 2


def test_risk_score_and_severity(member, project):
    r = client_for(member).post("/api/risks/", {"project": project.id, "title": "R",
                                                "probability": 4, "impact": 5})
    assert r.status_code == 201
    assert r.data["score"] == 20
    assert r.data["severity"] == "critical"
    assert client_for(member).post("/api/risks/", {"project": project.id, "title": "R",
                                                   "probability": 9, "impact": 1}).status_code == 400


def test_overview_analytics(member, manager, project):
    today = date.today()
    Task.objects.create(project=project, title="late", due_date=today - timedelta(days=3))
    Task.objects.create(project=project, title="ok", status="done")
    r = client_for(member).get("/api/analytics/overview/")
    assert r.status_code == 200
    assert r.data["total_tasks"] == 2
    assert r.data["overdue_tasks"] == 1
    assert r.data["completion_rate"] == 50.0


def test_project_summary_budget(member, project):
    t = Task.objects.create(project=project, title="t", estimate_hours=10)
    c = client_for(member)
    c.post("/api/time-entries/", {"task": t.id, "work_date": "2026-10-01", "hours": "20"})
    r = c.get(f"/api/analytics/projects/{project.id}/summary/")
    assert r.data["logged_hours"] == 20.0
    assert r.data["cost_to_date"] == 1000.0
    assert r.data["budget_used_percent"] == 10.0


def test_workload_and_velocity(member, project):
    Task.objects.create(project=project, title="t", assignee=member, estimate_hours=100)
    s = Sprint.objects.create(project=project, name="S1", start_date=date.today(),
                              end_date=date.today() + timedelta(days=14))
    Task.objects.create(project=project, title="d", sprint=s, story_points=5, status="done")
    Task.objects.create(project=project, title="o", sprint=s, story_points=3)
    c = client_for(member)
    wl = {row["username"]: row for row in c.get("/api/analytics/workload/").data}
    assert wl["mem"]["overloaded"] is True
    v = c.get("/api/analytics/velocity/").data[0]
    assert (v["planned_points"], v["completed_points"]) == (8, 5)


def test_audit_log_records_changes(manager, project):
    c = client_for(manager)
    tid = c.post("/api/tasks/", {"project": project.id, "title": "audited"}).data["id"]
    c.patch(f"/api/tasks/{tid}/", {"status": "in_progress"})
    log = c.get("/api/analytics/audit/").data
    actions = [e["action"] for e in log if e["entity"] == "Task" and e["entity_id"] == tid]
    assert "created" in actions and "updated" in actions
