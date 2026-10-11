import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.projects.models import Project
from apps.tasks.models import Task

pytestmark = pytest.mark.django_db


def mk(n, role):
    return User.objects.create_user(n, password="x" * 10, role=role)


def cl(u):
    c = APIClient()
    c.force_authenticate(u)
    return c


def move(u, t, status):
    return cl(u).patch(f"/api/tasks/{t.id}/", {"status": status}, format="json")


@pytest.fixture
def world():
    p = Project.objects.create(name="P", code="WF")
    return p, mk("mem", "member"), mk("lead", "lead"), mk("boss", "manager")


def test_default_is_free(world):
    p, mem, lead, boss = world
    t = Task.objects.create(project=p, title="T")
    assert move(mem, t, "done").status_code == 200


def test_transition_rules(world):
    p, mem, lead, boss = world
    p.workflow_transitions = {"todo": ["in_progress"], "in_progress": ["review"], "done": []}
    p.save()
    t = Task.objects.create(project=p, title="T")
    r = move(mem, t, "done")
    assert r.status_code == 400 and "does not allow" in str(r.data)
    assert move(mem, t, "in_progress").status_code == 200
    assert move(mem, t, "blocked").status_code == 400   # in_progress only allows review
    assert move(mem, t, "review").status_code == 200
    assert move(mem, t, "done").status_code == 200       # "review" has no rule: unrestricted
    assert move(boss, t, "todo").status_code == 400      # [] = locked, even for managers
    assert cl(mem).patch(f"/api/tasks/{t.id}/", {"title": "renamed"}, format="json").status_code == 200


def test_done_requires_approval(world):
    p, mem, lead, boss = world
    p.done_requires_approval = True
    p.save()
    t = Task.objects.create(project=p, title="T")
    r = move(mem, t, "done")
    assert r.status_code == 400 and "requires a lead" in str(r.data)
    assert move(mem, t, "review").status_code == 200
    assert move(lead, t, "done").status_code == 200
    assert Task.objects.get(pk=t.pk).completed_at is not None


def test_only_manager_edits_rules(world):
    p, mem, lead, boss = world
    body = {"workflow_transitions": {"todo": ["done"]}, "done_requires_approval": True}
    assert cl(mem).patch(f"/api/projects/{p.id}/", body, format="json").status_code == 400
    assert cl(boss).patch(f"/api/projects/{p.id}/", body, format="json").status_code == 200
    bad = cl(boss).patch(f"/api/projects/{p.id}/", {"workflow_transitions": {"todo": ["nope"]}}, format="json")
    assert bad.status_code == 400
    ok = cl(boss).patch(f"/api/projects/{p.id}/", {"workflow_transitions": None}, format="json")
    assert ok.status_code == 200 and ok.data["workflow_transitions"] is None
