from __future__ import annotations

from backend.flask_utils.app import app


def test_flask_utils_index_page():
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"CuraMind Utils" in response.data
    assert b"/utils/health" in response.data
    assert response.content_type.startswith("text/html")


def test_flask_utils_machine_endpoints():
    client = app.test_client()

    health_response = client.get("/health")
    version_response = client.get("/version")

    assert health_response.status_code == 200
    assert health_response.get_json() == {"status": "ok"}
    assert version_response.status_code == 200
    assert version_response.get_json() == {
        "service": "curamind-utils",
        "version": "1.0.0",
    }
