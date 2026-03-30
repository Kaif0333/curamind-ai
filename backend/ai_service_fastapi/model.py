from __future__ import annotations

import os
from datetime import datetime, timezone
from threading import Lock
import torch
import torchvision.transforms as T
from PIL import Image
from torchvision.models import resnet50

from .utils import create_heatmap, load_image_array

_model = None
_model_ready_at: str | None = None
_model_lock = Lock()
MODEL_NAME = os.getenv("AI_MODEL_NAME", "resnet50")
MODEL_VERSION = os.getenv("AI_MODEL_VERSION", "demo-resnet50-v1")
MODEL_REGISTRY = os.getenv("AI_MODEL_REGISTRY", "local-demo")
MODEL_WEIGHTS_SHA256 = os.getenv("AI_MODEL_WEIGHTS_SHA256", "")
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
        "model": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "model_registry": MODEL_REGISTRY,
        "weights_sha256": MODEL_WEIGHTS_SHA256,
        "device": "cpu",
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
    return {
        "anomaly_probability": anomaly_probability,
        "heatmap": heatmap,
        **get_model_metadata(),
    }
