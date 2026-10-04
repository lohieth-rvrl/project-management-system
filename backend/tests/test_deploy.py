import pytest
from django.core.management import call_command
from django.db import connection
from rest_framework.test import APIClient

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def test_health_needs_no_login_and_reports_db_up():
    r = APIClient().get("/api/health/")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "database": "up"}


def test_health_reports_503_when_database_fails(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("db down")

    monkeypatch.setattr(connection, "cursor", boom)
    r = APIClient().get("/api/health/")
    assert r.status_code == 503


def test_ensure_admin_creates_admin_and_can_log_in(monkeypatch):
    monkeypatch.setenv("DJANGO_SUPERUSER_USERNAME", "root")
    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "S3cure-pass-123")
    monkeypatch.setenv("DJANGO_SUPERUSER_EMAIL", "root@example.com")
    call_command("ensure_admin")
    u = User.objects.get(username="root")
    assert u.role == "admin" and u.is_superuser and u.is_staff
    r = APIClient().post("/api/auth/token/", {"username": "root", "password": "S3cure-pass-123"})
    assert r.status_code == 200


def test_ensure_admin_is_idempotent_and_updates_password(monkeypatch):
    monkeypatch.setenv("DJANGO_SUPERUSER_USERNAME", "root")
    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "first-password-1")
    call_command("ensure_admin")
    monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "second-password-2")
    call_command("ensure_admin")
    assert User.objects.filter(username="root").count() == 1
    assert User.objects.get(username="root").check_password("second-password-2")


def test_ensure_admin_skips_without_env(monkeypatch):
    monkeypatch.delenv("DJANGO_SUPERUSER_USERNAME", raising=False)
    monkeypatch.delenv("DJANGO_SUPERUSER_PASSWORD", raising=False)
    call_command("ensure_admin")
    assert User.objects.count() == 0
