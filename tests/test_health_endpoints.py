from __future__ import annotations

import pytest
from django.test import Client


@pytest.mark.django_db
def test_healthz_and_readyz_report_healthy_dependencies():
    client = Client()

    health_response = client.get("/healthz")
    ready_response = client.get("/readyz")

    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok", "service": "curamind-django"}
    assert ready_response.status_code == 200
    assert ready_response.json()["database"] is True
    assert ready_response.json()["cache"] is True


@pytest.mark.django_db
def test_readyz_returns_503_when_database_and_cache_are_unavailable(monkeypatch):
    from curamind_core import health as health_module

    class BrokenConnection:
        def cursor(self):
            raise RuntimeError("database unavailable")

    class BrokenConnections:
        def __getitem__(self, _alias):
            return BrokenConnection()

    class BrokenCache:
        def set(self, *_args, **_kwargs):
            raise RuntimeError("cache unavailable")

        def get(self, *_args, **_kwargs):
            return None

        def delete(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(health_module, "connections", BrokenConnections())
    monkeypatch.setattr(health_module, "cache", BrokenCache())

    client = Client()
    response = client.get("/readyz")

    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "service": "curamind-django",
        "database": False,
        "cache": False,
    }
