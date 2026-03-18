from __future__ import annotations

import os

import requests

from apps.ai_engine.mongo import store_ai_result

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://fastapi:8001")


def request_inference(image_bytes: bytes, image_id: str) -> dict:
    response = requests.post(
        f"{AI_SERVICE_URL}/analyze-image",
        files={"file": ("image", image_bytes)},
        timeout=120,
    )
    response.raise_for_status()
    payload = response.json()
    store_ai_result(image_id, payload)
    return payload
