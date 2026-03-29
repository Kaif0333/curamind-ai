from __future__ import annotations

import uuid

from django.core.cache import cache
from django.db import connections
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def healthz(_request):
    return JsonResponse({"status": "ok", "service": "curamind-django"})


@require_GET
def readyz(_request):
    db_ready = False
    cache_ready = False

    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        db_ready = True
    except Exception:
        db_ready = False

    cache_key = f"curamind-ready:{uuid.uuid4()}"
    try:
        cache.set(cache_key, "ok", timeout=5)
        cache_ready = cache.get(cache_key) == "ok"
        cache.delete(cache_key)
    except Exception:
        cache_ready = False

    ready = db_ready and cache_ready
    status_code = 200 if ready else 503
    return JsonResponse(
        {
            "status": "ready" if ready else "degraded",
            "service": "curamind-django",
            "database": db_ready,
            "cache": cache_ready,
        },
        status=status_code,
    )
