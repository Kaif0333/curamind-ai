from __future__ import annotations

import os

import requests
from requests import RequestException

from apps.ai_engine.mongo import store_ai_result

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://fastapi:8001")
REQUIRED_RESULT_FIELDS = {"anomaly_probability", "heatmap", "model"}


class AIInferenceError(RuntimeError):
    """Base error for AI inference integration failures."""


class AIServiceRequestError(AIInferenceError):
    """Raised when the inference service cannot be reached or returns an HTTP error."""


class AIServiceResponseError(AIInferenceError):
    """Raised when the inference service returns malformed or incomplete data."""


def _validate_inference_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise AIServiceResponseError("AI inference service returned an invalid payload.")

    missing_fields = REQUIRED_RESULT_FIELDS - payload.keys()
    if missing_fields:
        raise AIServiceResponseError(
            "AI inference service returned an incomplete payload: "
            + ", ".join(sorted(missing_fields))
        )

    try:
        payload["anomaly_probability"] = float(payload["anomaly_probability"])
    except (TypeError, ValueError) as exc:
        raise AIServiceResponseError(
            "AI inference service returned an invalid anomaly probability."
        ) from exc

    if not isinstance(payload["heatmap"], str) or not isinstance(payload["model"], str):
        raise AIServiceResponseError("AI inference service returned malformed result fields.")

    for optional_field in ("model_version", "device"):
        if optional_field in payload and payload[optional_field] is not None:
            if not isinstance(payload[optional_field], str):
                raise AIServiceResponseError(
                    f"AI inference service returned an invalid {optional_field}."
                )

    return payload


def request_inference(image_bytes: bytes, image_id: str) -> dict:
    try:
        response = requests.post(
            f"{AI_SERVICE_URL}/analyze-image",
            files={"file": ("image.bin", image_bytes, "application/octet-stream")},
            timeout=120,
        )
        response.raise_for_status()
    except RequestException as exc:
        raise AIServiceRequestError("AI inference service request failed.") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise AIServiceResponseError("AI inference service returned invalid JSON.") from exc

    payload = _validate_inference_payload(payload)
    store_ai_result(image_id, payload)
    return payload
