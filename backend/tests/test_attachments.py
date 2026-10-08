import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.projects.models import Project
from apps.tasks.models import Attachment, Task

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def cl(u):
    c = APIClient()
    c.force_authenticate(u)
    return c


@pytest.fixture
def setup():
    m = User.objects.create_user("mem", password="x" * 10, role="member")
    v = User.objects.create_user("view", password="x" * 10, role="viewer")
    p = Project.objects.create(name="P", code="AT")
    return m, v, Task.objects.create(project=p, title="T", reporter=m)


def up(c, task, name="spec.txt", data=b"hello"):
    return c.post("/api/attachments/", {"task": task.id, "file": SimpleUploadedFile(name, data)}, format="multipart")


def test_upload_list_download_delete(setup):
    m, v, t = setup
    r = up(cl(m), t)
    assert r.status_code == 201, r.data
    assert r.data["name"] == "spec.txt" and r.data["size"] == 5 and "file" not in r.data
    aid = r.data["id"]
    assert cl(v).get(f"/api/attachments/?task={t.id}").data["count"] == 1
    d = cl(v).get(f"/api/attachments/{aid}/download/")
    assert d.status_code == 200 and b"".join(d.streaming_content) == b"hello"
    assert "attachment" in d["Content-Disposition"]
    assert cl(m).delete(f"/api/attachments/{aid}/").status_code == 403  # members cannot delete
    boss = User.objects.create_user("boss", password="x" * 10, role="manager")
    assert cl(boss).delete(f"/api/attachments/{aid}/").status_code == 204
    assert Attachment.objects.count() == 0


def test_download_needs_login(setup):
    m, v, t = setup
    aid = up(cl(m), t).data["id"]
    assert APIClient().get(f"/api/attachments/{aid}/download/").status_code == 401


def test_viewer_cannot_upload(setup):
    m, v, t = setup
    assert up(cl(v), t).status_code == 403


def test_blocked_type_and_size(setup, settings):
    m, v, t = setup
    assert up(cl(m), t, "run.exe").status_code == 400
    assert up(cl(m), t, "page.HTML").status_code == 400
    settings.MAX_UPLOAD_MB = 0
    assert up(cl(m), t, "big.txt", b"x").status_code == 400
    assert Attachment.objects.count() == 0


def test_path_in_name_is_stripped(setup):
    m, v, t = setup
    r = up(cl(m), t, "../../etc/evil.txt")
    assert r.status_code == 201 and r.data["name"] == "evil.txt"
