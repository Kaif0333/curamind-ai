from __future__ import annotations

import importlib
import sys
import types

from fastapi.testclient import TestClient

fake_model = types.ModuleType("backend.ai_service_fastapi.model")
setattr(
    fake_model,
    "predict_image",
    lambda _: {
        "anomaly_probability": 0.12,
        "heatmap": "abc",
        "model": "resnet50",
        "model_version": "demo",
        "device": "cpu",
    },
)
setattr(
    fake_model,
    "get_model_metadata",
    lambda: {"model": "resnet50", "model_version": "demo", "device": "cpu"},
)
setattr(
    fake_model,
    "warmup_model",
    lambda: {"model": "resnet50", "model_version": "demo", "device": "cpu"},
)
fake_mongo = types.ModuleType("backend.ai_service_fastapi.mongo")
setattr(fake_mongo, "get_ai_result", lambda image_id: None)
setattr(fake_mongo, "check_mongo_connection", lambda: True)

sys.modules["backend.ai_service_fastapi.model"] = fake_model
sys.modules["backend.ai_service_fastapi.mongo"] = fake_mongo

fastapi_main = importlib.import_module("backend.ai_service_fastapi.main")
client = TestClient(fastapi_main.app)


def test_analyze_image_returns_prediction(monkeypatch):
    monkeypatch.setattr(
        fastapi_main,
        "predict_image",
        lambda _: {
            "anomaly_probability": 0.12,
            "heatmap": "abc",
            "model": "resnet50",
            "model_version": "demo",
            "device": "cpu",
        },
    )

    response = client.post(
        "/analyze-image",
        files={"file": ("scan.png", b"fake-image", "image/png")},
    )

    assert response.status_code == 200
    assert response.json()["model"] == "resnet50"


def test_health_and_model_info_endpoints(monkeypatch):
    monkeypatch.setattr(
        fastapi_main,
        "get_model_metadata",
        lambda: {"model": "resnet50", "model_version": "demo", "device": "cpu"},
    )

    health_response = client.get("/health")
    model_response = client.get("/model-info")

    assert health_response.status_code == 200
    assert health_response.json()["service"] == "curamind-ai-inference"
    assert model_response.status_code == 200
    assert model_response.json()["model_version"] == "demo"


def test_ready_endpoint_requires_model_and_mongo(monkeypatch):
    monkeypatch.setattr(
        fastapi_main,
        "warmup_model",
        lambda: {"model": "resnet50", "model_version": "demo", "device": "cpu"},
    )
    monkeypatch.setattr(fastapi_main, "check_mongo_connection", lambda: True)

    ready_response = client.get("/ready")
    assert ready_response.status_code == 200
    assert ready_response.json()["status"] == "ready"

    monkeypatch.setattr(fastapi_main, "check_mongo_connection", lambda: False)
    degraded_response = client.get("/ready")
    assert degraded_response.status_code == 503


def test_analyze_image_rejects_unsupported_types_and_oversized_files(monkeypatch):
    monkeypatch.setattr(fastapi_main, "MAX_UPLOAD_BYTES", 4)
    monkeypatch.setattr(fastapi_main, "MAX_UPLOAD_MB", 0)

    unsupported = client.post(
        "/analyze-image",
        files={"file": ("scan.txt", b"hello", "text/plain")},
    )
    oversized = client.post(
        "/analyze-image",
        files={"file": ("scan.png", b"12345", "image/png")},
    )

    assert unsupported.status_code == 415
    assert oversized.status_code == 413


def test_analyze_image_rejects_empty_payload():
    response = client.post(
        "/analyze-image",
        files={"file": ("empty.png", b"", "image/png")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Empty file"


def test_analyze_image_returns_decode_error(monkeypatch):
    monkeypatch.setattr(
        fastapi_main,
        "predict_image",
        lambda _: (_ for _ in ()).throw(ValueError("Unable to decode image")),
    )

    response = client.post(
        "/analyze-image",
        files={"file": ("broken.bin", b"broken", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unable to decode image"


def test_ai_result_returns_document(monkeypatch):
    monkeypatch.setattr(
        fastapi_main,
        "get_ai_result",
        lambda image_id: {"image_id": image_id, "anomaly_probability": 0.77},
    )

    response = client.get("/ai-result", params={"image_id": "img-123"})

    assert response.status_code == 200
    assert response.json()["anomaly_probability"] == 0.77


def test_ai_result_returns_404(monkeypatch):
    monkeypatch.setattr(fastapi_main, "get_ai_result", lambda _: None)

    response = client.get("/ai-result", params={"image_id": "missing"})

    assert response.status_code == 404
    assert response.json()["detail"] == "AI result not found"
