import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.projects.models import Project
from apps.tasks.models import Task

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    u = User.objects.create_user(username="pg", password="pass12345", role="manager")
    c = APIClient()
    c.force_authenticate(u)
    return c


@pytest.fixture
def many_tasks():
    p = Project.objects.create(code="PG", name="Pagination")
    Task.objects.bulk_create([Task(project=p, title=f"t{i}") for i in range(230)])
    return p


def test_default_page_size_is_25(client, many_tasks):
    r = client.get("/api/tasks/")
    assert r.data["count"] == 230
    assert len(r.data["results"]) == 25
    assert r.data["next"] is not None


def test_page_size_param_is_honoured(client, many_tasks):
    r = client.get("/api/tasks/?page_size=100")
    assert len(r.data["results"]) == 100


def test_page_size_is_capped_at_200(client, many_tasks):
    r = client.get("/api/tasks/?page_size=500")
    assert len(r.data["results"]) == 200


def test_second_page_has_different_rows(client, many_tasks):
    first = {t["id"] for t in client.get("/api/tasks/?page_size=50").data["results"]}
    second = {t["id"] for t in client.get("/api/tasks/?page_size=50&page=2").data["results"]}
    assert first.isdisjoint(second) and len(second) == 50


def test_last_partial_page(client, many_tasks):
    r = client.get("/api/tasks/?page_size=100&page=3")
    assert len(r.data["results"]) == 30
    assert r.data["next"] is None
