from __future__ import annotations

import hashlib
import logging
import os
import time

import requests
from requests import HTTPError, RequestException

from apps.ai_engine.mongo import store_ai_result

logger = logging.getLogger(__name__)
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://fastapi:8001")
AI_SERVICE_TIMEOUT_SECONDS = float(os.getenv("AI_SERVICE_TIMEOUT_SECONDS", "120"))
AI_SERVICE_RETRY_COUNT = max(0, int(os.getenv("AI_SERVICE_RETRY_COUNT", "2")))
AI_SERVICE_RETRY_BACKOFF_SECONDS = float(os.getenv("AI_SERVICE_RETRY_BACKOFF_SECONDS", "1"))
REQUIRED_RESULT_FIELDS = {"anomaly_probability", "heatmap", "model"}


class AIInferenceError(RuntimeError):
    """Base error for AI inference integration failures."""


class AIServiceRequestError(AIInferenceError):
    """Raised when the inference service cannot be reached or returns an HTTP error."""


class AIServiceResponseError(AIInferenceError):
    """Raised when the inference service returns malformed or incomplete data."""


def _should_retry_request(exc: RequestException) -> bool:
    if isinstance(exc, HTTPError) and exc.response is not None:
        return exc.response.status_code >= 500
    response = getattr(exc, "response", None)
    if response is not None:
        return response.status_code >= 500
    return True


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

    for optional_field in (
        "model_version",
        "device",
        "model_registry",
        "weights_sha256",
        "input_sha256",
        "image_id",
    ):
        if optional_field in payload and payload[optional_field] is not None:
            if not isinstance(payload[optional_field], str):
                raise AIServiceResponseError(
                    f"AI inference service returned an invalid {optional_field}."
                )

    if "service_processing_ms" in payload and payload["service_processing_ms"] is not None:
        try:
            payload["service_processing_ms"] = float(payload["service_processing_ms"])
        except (TypeError, ValueError) as exc:
            raise AIServiceResponseError(
                "AI inference service returned an invalid service_processing_ms."
            ) from exc

    return payload


def request_inference(image_bytes: bytes, image_id: str) -> dict:
    response = None
    last_error: RequestException | None = None
    image_sha256 = hashlib.sha256(image_bytes).hexdigest()
    for attempt in range(AI_SERVICE_RETRY_COUNT + 1):
        try:
            response = requests.post(
                f"{AI_SERVICE_URL}/analyze-image",
                headers={
                    "X-Image-Id": image_id,
                    "X-Image-SHA256": image_sha256,
                },
                files={"file": ("image.bin", image_bytes, "application/octet-stream")},
                timeout=AI_SERVICE_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            break
        except RequestException as exc:
            last_error = exc
            if attempt >= AI_SERVICE_RETRY_COUNT or not _should_retry_request(exc):
                raise AIServiceRequestError("AI inference service request failed.") from exc
            backoff_seconds = AI_SERVICE_RETRY_BACKOFF_SECONDS * (2**attempt)
            logger.warning(
                "Retrying AI inference request for image %s after transient failure on attempt %s",
                image_id,
                attempt + 1,
            )
            time.sleep(backoff_seconds)

    if response is None:
        raise AIServiceRequestError("AI inference service request failed.") from last_error

    try:
        payload = response.json()
    except ValueError as exc:
        raise AIServiceResponseError("AI inference service returned invalid JSON.") from exc

    payload = _validate_inference_payload(payload)
    payload.setdefault("image_id", image_id)
    payload.setdefault(
        "input_sha256",
        response.headers.get("X-Image-SHA256", image_sha256),
    )
    if "service_processing_ms" not in payload:
        process_time_header = response.headers.get("X-Process-Time-Ms")
        if process_time_header:
            try:
                payload["service_processing_ms"] = float(process_time_header)
            except (TypeError, ValueError):
                logger.warning(
                    "AI inference service returned a non-numeric "
                    "X-Process-Time-Ms header for image %s",
                    image_id,
                )
    store_ai_result(image_id, payload)
    return payload
