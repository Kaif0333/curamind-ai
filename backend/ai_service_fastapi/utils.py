from __future__ import annotations

import base64
from io import BytesIO

import cv2
import numpy as np
import pydicom
from PIL import Image


def load_image_array(image_bytes: bytes) -> np.ndarray:
    try:
        dataset = pydicom.dcmread(BytesIO(image_bytes))
        array = dataset.pixel_array.astype("uint8")
        if array.ndim == 2:
            array = cv2.cvtColor(array, cv2.COLOR_GRAY2RGB)
        return array
    except Exception:
        pass
    array = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if array is not None:
        return cv2.cvtColor(array, cv2.COLOR_BGR2RGB)
    try:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        return np.array(image)
    except Exception as exc:
        raise ValueError("Unable to decode image") from exc


def create_heatmap(array: np.ndarray) -> str:
    gray = cv2.cvtColor(array, cv2.COLOR_RGB2GRAY)
    heatmap = cv2.applyColorMap(gray, cv2.COLORMAP_JET)
    success, buffer = cv2.imencode(".png", heatmap)
    if not success:
        return ""
    return base64.b64encode(buffer.tobytes()).decode("ascii")
