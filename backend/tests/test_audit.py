import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.projects.models import Project
from apps.risks.models import Risk
from apps.tasks.models import Task
from apps.timesheets.models import TimeEntry

pytestmark = pytest.mark.django_db


@pytest.fixture
def c():
    u = User.objects.create_user("aud", password="x" * 10, role="manager")
    cl = APIClient()
    cl.force_authenticate(u)
    return cl


def test_covers_risks_timesheets_users_and_milestones(c):
    p = Project.objects.create(name="P", code="AU")
    t = Task.objects.create(project=p, title="T")
    Risk.objects.create(project=p, title="R", probability=1, impact=1)
    TimeEntry.objects.create(task=t, user=User.objects.get(username="aud"), work_date="2026-01-01", hours=2)
    kinds = {e["entity"] for e in c.get("/api/analytics/audit/?page_size=200").data["results"]}
    assert {"Project", "Task", "Risk", "Timesheet", "User"} <= kinds


def test_pagination_counts_and_order(c):
    p = Project.objects.create(name="P", code="AU")
    for i in range(30):
        Task.objects.create(project=p, title=f"T{i}")
    first = c.get("/api/analytics/audit/?entity=Task&page_size=10").data
    assert first["count"] == 30 and len(first["results"]) == 10 and first["next"] and not first["previous"]
    last = c.get("/api/analytics/audit/?entity=Task&page_size=10&page=3").data
    assert len(last["results"]) == 10 and last["next"] is None and last["previous"]
    seen = [e["entity_id"] for pg in (1, 2, 3) for e in c.get(f"/api/analytics/audit/?entity=Task&page_size=10&page={pg}").data["results"]]
    assert len(set(seen)) == 30  # no row repeated or skipped across pages
    ats = [e["at"] for e in first["results"]]
    assert ats == sorted(ats, reverse=True)


def test_filters_and_validation(c):
    p = Project.objects.create(name="P", code="AU")
    t = Task.objects.create(project=p, title="T")
    t.delete()
    deleted = c.get("/api/analytics/audit/?entity=Task&action=deleted").data
    assert deleted["count"] == 1 and deleted["results"][0]["action"] == "deleted"
    assert c.get("/api/analytics/audit/?entity=Nope").status_code == 400
    assert c.get("/api/analytics/audit/?action=boom").status_code == 400
    assert c.get("/api/analytics/audit/?page_size=abc&page=zzz").status_code == 200
    assert c.get("/api/analytics/audit/?user=nobody").data["count"] == 0
