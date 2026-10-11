from datetime import date, datetime, timedelta, timezone as tz

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.projects.models import Project
from apps.tasks.models import Task
from apps.timesheets.models import TimeEntry

pytestmark = pytest.mark.django_db


@pytest.fixture
def c():
    u = User.objects.create_user("ch", password="x" * 10, role="viewer")
    cl = APIClient()
    cl.force_authenticate(u)
    return cl


def test_burndown_counts_open_work_per_day(c):
    today = date.today()
    start = today - timedelta(days=4)
    p = Project.objects.create(name="P", code="BD", start_date=start, end_date=today + timedelta(days=4))
    a = Task.objects.create(project=p, title="a", estimate_hours=5)
    b = Task.objects.create(project=p, title="b", estimate_hours=3)
    Task.objects.filter(pk__in=[a.pk, b.pk]).update(created_at=datetime.combine(start, datetime.min.time(), tz.utc))
    Task.objects.filter(pk=a.pk).update(status="done", completed_at=datetime.combine(today - timedelta(days=2), datetime.min.time(), tz.utc))
    d = c.get(f"/api/analytics/projects/{p.id}/burndown/").data
    assert d["days"][0] == start.isoformat() and d["days"][-1] == (today + timedelta(days=4)).isoformat()
    assert d["remaining"][:2] == [2, 2] and d["remaining"][2] == 1   # a done on day 3
    assert d["ideal"][0] == 2 and d["ideal"][-1] == 0
    assert c.get(f"/api/analytics/projects/{p.id}/burndown/?unit=hours").data["remaining"][0] == 8


def test_burndown_empty_project(c):
    p = Project.objects.create(name="E", code="EB")
    assert c.get(f"/api/analytics/projects/{p.id}/burndown/").data["days"] == []


def test_budget_trend_is_cumulative(c):
    p = Project.objects.create(name="P", code="BT", budget=1000, hourly_rate=10)
    t = Task.objects.create(project=p, title="t")
    u = User.objects.get(username="ch")
    TimeEntry.objects.create(task=t, user=u, work_date=date(2026, 1, 5), hours=10)   # Monday
    TimeEntry.objects.create(task=t, user=u, work_date=date(2026, 1, 7), hours=5)    # same week
    TimeEntry.objects.create(task=t, user=u, work_date=date(2026, 1, 13), hours=2)   # next week
    d = c.get(f"/api/analytics/projects/{p.id}/budget-trend/").data
    assert d["weeks"] == ["2026-01-05", "2026-01-12"] and d["cumulative_cost"] == [150, 170]
    assert d["budget"] == 1000
