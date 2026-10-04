from django.db import connection
from django.http import JsonResponse


def health(request):
    """Liveness + database check for the hosting platform. No auth required."""
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
    except Exception:
        return JsonResponse({"status": "error", "database": "down"}, status=503)
    return JsonResponse({"status": "ok", "database": "up"})
