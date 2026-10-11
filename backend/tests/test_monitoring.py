import pytest
from rest_framework.test import APIClient

from apps.projects.models import Project
from apps.tasks.models import Task
from config.monitoring import init_sentry

pytestmark = pytest.mark.django_db


def test_metrics_off_without_token(settings):
    settings.METRICS_TOKEN = ""
    assert APIClient().get("/api/metrics/").status_code == 404


def test_metrics_needs_correct_token(settings):
    settings.METRICS_TOKEN = "s3cret-token"
    c = APIClient()
    assert c.get("/api/metrics/").status_code == 401
    assert c.get("/api/metrics/", HTTP_AUTHORIZATION="Bearer wrong").status_code == 401


def test_metrics_exposes_app_and_request_numbers(settings):
    settings.METRICS_TOKEN = "s3cret-token"
    p = Project.objects.create(name="P", code="MT")
    Task.objects.create(project=p, title="t")
    c = APIClient()
    c.get("/api/health/")
    r = c.get("/api/metrics/", HTTP_AUTHORIZATION="Bearer s3cret-token")
    body = r.content.decode()
    assert r.status_code == 200
    assert 'pms_tasks{status="todo"} 1.0' in body
    assert "pms_http_requests_total" in body and "pms_active_users" in body
    assert "api/metrics/" not in body.split("pms_http_requests_total")[1].split("# HELP")[0]


def test_sentry_is_off_without_dsn_and_starts_with_one():
    assert init_sentry("") is False
    try:
        assert init_sentry("https://abc@o0.ingest.sentry.io/1", "test") is True
    finally:
        import sentry_sdk
        sentry_sdk.get_client().close()  # do not leave a live client behind for other tests
        sentry_sdk.init(dsn="")
