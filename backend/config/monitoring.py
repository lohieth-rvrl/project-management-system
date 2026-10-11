"""Error tracking (Sentry) and Prometheus metrics. Both stay off until configured."""
import os
import time

from django.http import HttpResponse, HttpResponseNotFound
from django.utils.crypto import constant_time_compare


def init_sentry(dsn, environment="production", traces_sample_rate=0.0):
    """Start Sentry when a DSN is given. No personal data is sent."""
    if not dsn:
        return False
    import sentry_sdk

    sentry_sdk.init(dsn=dsn, environment=environment, send_default_pii=False,
                    traces_sample_rate=traces_sample_rate)
    return True


# ---- Prometheus -----------------------------------------------------------------
# gunicorn runs several worker processes, so counters are shared through files in this folder.
os.environ.setdefault("PROMETHEUS_MULTIPROC_DIR", "/tmp/pms_prometheus")
os.makedirs(os.environ["PROMETHEUS_MULTIPROC_DIR"], exist_ok=True)

from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest  # noqa: E402
from prometheus_client import CONTENT_TYPE_LATEST, multiprocess  # noqa: E402
from prometheus_client.core import GaugeMetricFamily  # noqa: E402

REQUESTS = Counter("pms_http_requests_total", "HTTP requests", ["method", "route", "status"])
LATENCY = Histogram("pms_http_request_seconds", "Request time in seconds", ["method", "route"],
                    buckets=(0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10))


class MetricsMiddleware:
    """Counts requests and times them, labelled by URL pattern (not the raw URL)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.perf_counter()
        response = self.get_response(request)
        match = getattr(request, "resolver_match", None)
        route = match.route if match else "unmatched"
        if route != "api/metrics/":
            REQUESTS.labels(request.method, route, str(response.status_code)).inc()
            LATENCY.labels(request.method, route).observe(time.perf_counter() - started)
        return response


class AppStateCollector:
    """Live counts read from the database each time Prometheus scrapes."""

    def collect(self):
        from django.db.models import Count
        from django.utils import timezone

        from apps.accounts.models import User
        from apps.projects.models import Project
        from apps.risks.models import Risk
        from apps.tasks.models import Task

        tasks = GaugeMetricFamily("pms_tasks", "Tasks by status", labels=["status"])
        for row in Task.objects.values("status").annotate(n=Count("id")):
            tasks.add_metric([row["status"]], row["n"])
        yield tasks
        overdue = GaugeMetricFamily("pms_tasks_overdue", "Open tasks past their due date")
        overdue.add_metric([], Task.objects.filter(due_date__lt=timezone.localdate()).exclude(status="done").count())
        yield overdue
        projects = GaugeMetricFamily("pms_projects", "Projects by status", labels=["status"])
        for row in Project.objects.values("status").annotate(n=Count("id")):
            projects.add_metric([row["status"]], row["n"])
        yield projects
        risks = GaugeMetricFamily("pms_open_risks", "Risks that are not closed")
        risks.add_metric([], Risk.objects.exclude(status="closed").count())
        yield risks
        users = GaugeMetricFamily("pms_active_users", "Active user accounts")
        users.add_metric([], User.objects.filter(is_active=True).count())
        yield users


def metrics_view(request):
    """GET /api/metrics/ with 'Authorization: Bearer <METRICS_TOKEN>'. Off (404) when no token is set."""
    from django.conf import settings

    token = getattr(settings, "METRICS_TOKEN", "")
    if not token:
        return HttpResponseNotFound()
    given = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    if not constant_time_compare(given, token):
        return HttpResponse("Unauthorized", status=401)
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)
    registry.register(AppStateCollector())
    return HttpResponse(generate_latest(registry), content_type=CONTENT_TYPE_LATEST)
