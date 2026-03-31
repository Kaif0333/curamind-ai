from __future__ import annotations

import os
from datetime import datetime, timezone
from threading import Lock

import torch
import torchvision.transforms as T
from PIL import Image
from torchvision.models import resnet50

from .model_registry import resolve_model_metadata
from .utils import create_heatmap, load_image_array

_model = None
_model_ready_at: str | None = None
_model_lock = Lock()
MODEL_NAME = os.getenv("AI_MODEL_NAME", "resnet50")
MODEL_VERSION = os.getenv("AI_MODEL_VERSION", "demo-resnet50-v1")
MODEL_REGISTRY = os.getenv("AI_MODEL_REGISTRY", "")
MODEL_WEIGHTS_SHA256 = os.getenv("AI_MODEL_WEIGHTS_SHA256", "")
ENV_ANOMALY_THRESHOLD = os.getenv("AI_MODEL_ANOMALY_THRESHOLD", "").strip()


def _get_env_anomaly_threshold() -> float | None:
    if not ENV_ANOMALY_THRESHOLD:
        return None
    try:
        return float(ENV_ANOMALY_THRESHOLD)
    except ValueError:
        return None


MODEL_METADATA = resolve_model_metadata(
    model_name=MODEL_NAME,
    requested_version=MODEL_VERSION,
    env_registry_name=MODEL_REGISTRY,
    env_weights_sha256=MODEL_WEIGHTS_SHA256,
    env_anomaly_threshold=_get_env_anomaly_threshold(),
)
_transform = T.Compose(
    [
        T.Resize((224, 224)),
        T.ToTensor(),
        T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ]
)


def _get_model():
    global _model
    global _model_ready_at
    if _model is None:
        with _model_lock:
            if _model is None:
                _model = resnet50(weights=None)
                _model.eval()
                _model_ready_at = datetime.now(timezone.utc).isoformat()
    return _model


def get_model_metadata() -> dict[str, object]:
    metadata: dict[str, object] = {
        **MODEL_METADATA,
        "ready": _model is not None,
    }
    if _model_ready_at:
        metadata["ready_at"] = _model_ready_at
    return metadata


def warmup_model() -> dict[str, object]:
    _get_model()
    return get_model_metadata()


def predict_image(image_bytes: bytes) -> dict[str, object]:
    array = load_image_array(image_bytes)
    image = Image.fromarray(array).convert("RGB")
    tensor = _transform(image).unsqueeze(0)
    model = _get_model()
    with torch.no_grad():
        logits = model(tensor)
        probs = torch.softmax(logits, dim=1)
        max_prob = float(probs.max().item())
    anomaly_probability = float(1.0 - max_prob)
    heatmap = create_heatmap(array)
    threshold = float(MODEL_METADATA.get("anomaly_threshold", 0.5))
    return {
        "anomaly_probability": anomaly_probability,
        "heatmap": heatmap,
        "anomaly_threshold": threshold,
        "is_anomalous": anomaly_probability >= threshold,
        "model": MODEL_METADATA["model"],
        "model_version": MODEL_METADATA["model_version"],
        "model_registry": MODEL_METADATA["model_registry"],
        "weights_sha256": MODEL_METADATA["weights_sha256"],
        "device": MODEL_METADATA["device"],
    }
