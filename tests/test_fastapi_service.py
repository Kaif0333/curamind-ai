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
    },
)
fake_mongo = types.ModuleType("backend.ai_service_fastapi.mongo")
setattr(fake_mongo, "get_ai_result", lambda image_id: None)

sys.modules["backend.ai_service_fastapi.model"] = fake_model
sys.modules["backend.ai_service_fastapi.mongo"] = fake_mongo

fastapi_main = importlib.import_module("backend.ai_service_fastapi.main")
client = TestClient(fastapi_main.app)


def test_analyze_image_returns_prediction(monkeypatch):
    monkeypatch.setattr(
        fastapi_main,
        "predict_image",
        lambda _: {"anomaly_probability": 0.12, "heatmap": "abc", "model": "resnet50"},
    )

    response = client.post(
        "/analyze-image",
        files={"file": ("scan.png", b"fake-image", "image/png")},
    )

    assert response.status_code == 200
    assert response.json()["model"] == "resnet50"


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
