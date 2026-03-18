from __future__ import annotations

from typing import Dict

import torch
import torchvision.transforms as T
from PIL import Image
from torchvision.models import resnet50

from .utils import create_heatmap, load_image_array

_model = None
_transform = T.Compose(
    [
        T.Resize((224, 224)),
        T.ToTensor(),
        T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ]
)


def _get_model():
    global _model
    if _model is None:
        _model = resnet50(weights=None)
        _model.eval()
    return _model


def predict_image(image_bytes: bytes) -> Dict:
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
        "model": "resnet50",
    }
