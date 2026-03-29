from __future__ import annotations

import base64
from io import BytesIO

import cv2
import numpy as np
import pydicom
from PIL import Image


def normalize_to_uint8(array: np.ndarray) -> np.ndarray:
    if array.dtype == np.uint8:
        return array

    float_array = array.astype("float32")
    min_value = float(np.min(float_array))
    max_value = float(np.max(float_array))
    if max_value <= min_value:
        return np.zeros(float_array.shape, dtype=np.uint8)
    normalized = (float_array - min_value) / (max_value - min_value)
    return np.clip(normalized * 255.0, 0, 255).astype("uint8")


def load_image_array(image_bytes: bytes) -> np.ndarray:
    try:
        dataset = pydicom.dcmread(BytesIO(image_bytes))
        array = normalize_to_uint8(dataset.pixel_array)
        if array.ndim == 2:
            array = cv2.cvtColor(array, cv2.COLOR_GRAY2RGB)
        elif array.ndim == 3 and array.shape[-1] == 1:
            array = np.repeat(array, 3, axis=2)
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
