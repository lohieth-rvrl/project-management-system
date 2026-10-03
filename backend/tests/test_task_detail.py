import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.projects.models import Project
from apps.tasks.models import Comment, Sprint, Task

pytestmark = pytest.mark.django_db


def user(name, role):
    return User.objects.create_user(username=name, password="pass12345", role=role)


def as_user(u):
    c = APIClient()
    c.force_authenticate(u)
    return c


@pytest.fixture
def task():
    p = Project.objects.create(code="TD", name="Task detail")
    return Task.objects.create(project=p, title="original")


def test_edit_all_detail_fields(task):
    from datetime import date
    worker = user("w", "member")
    sprint = Sprint.objects.create(project=task.project, name="S1",
                                   start_date=date(2026, 10, 1), end_date=date(2026, 10, 14))
    payload = {
        "title": "renamed", "description": "details", "status": "review", "priority": "high",
        "assignee": worker.id, "sprint": sprint.id, "start_date": "2026-10-02",
        "due_date": "2026-10-10", "estimate_hours": "6.5", "story_points": 5,
    }
    r = as_user(worker).patch(f"/api/tasks/{task.id}/", payload, format="json")
    assert r.status_code == 200
    task.refresh_from_db()
    assert (task.title, task.status, task.assignee_id, task.sprint_id, task.story_points) == (
        "renamed", "review", worker.id, sprint.id, 5)


def test_clearing_assignee_sprint_and_dates_with_null(task):
    worker = user("w2", "member")
    task.assignee = worker
    task.due_date = "2026-10-10"
    task.save()
    r = as_user(worker).patch(f"/api/tasks/{task.id}/",
                              {"assignee": None, "sprint": None, "due_date": None}, format="json")
    assert r.status_code == 200
    task.refresh_from_db()
    assert task.assignee_id is None and task.due_date is None


def test_comments_filtered_by_task_and_author_is_current_user(task):
    other = Task.objects.create(project=task.project, title="other")
    member = user("m", "member")
    c = as_user(member)
    r = c.post("/api/comments/", {"task": task.id, "body": "first"})
    assert r.status_code == 201 and r.data["author"] == member.id
    c.post("/api/comments/", {"task": other.id, "body": "elsewhere"})
    rows = c.get(f"/api/comments/?task={task.id}").data["results"]
    assert [x["body"] for x in rows] == ["first"]
    assert rows[0]["author_name"] == "m"


def test_viewer_cannot_comment_or_edit(task):
    v = as_user(user("v", "viewer"))
    assert v.post("/api/comments/", {"task": task.id, "body": "x"}).status_code == 403
    assert v.patch(f"/api/tasks/{task.id}/", {"title": "x"}).status_code == 403
    assert Comment.objects.count() == 0


def test_member_cannot_delete_task_manager_can(task):
    assert as_user(user("m2", "member")).delete(f"/api/tasks/{task.id}/").status_code == 403
    assert as_user(user("boss", "manager")).delete(f"/api/tasks/{task.id}/").status_code == 204


def test_user_list_available_for_assignee_picker(task):
    user("picker", "member")
    r = as_user(user("m3", "member")).get("/api/users/?page_size=200")
    assert r.status_code == 200
    assert {"id", "full_name", "role", "is_active"} <= set(r.data["results"][0])
