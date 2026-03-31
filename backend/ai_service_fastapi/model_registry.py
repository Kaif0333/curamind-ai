from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)
MODEL_REGISTRY_PATH = Path(__file__).with_name("model_registry.json")


@lru_cache(maxsize=1)
def load_model_registry() -> dict[str, Any]:
    try:
        with MODEL_REGISTRY_PATH.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        logger.warning("Model registry file not found at %s", MODEL_REGISTRY_PATH)
    except json.JSONDecodeError:
        logger.exception("Model registry file is not valid JSON: %s", MODEL_REGISTRY_PATH)
    return {}


def resolve_model_metadata(
    model_name: str,
    requested_version: str,
    env_registry_name: str,
    env_weights_sha256: str,
    env_anomaly_threshold: float | None,
) -> dict[str, Any]:
    registry = load_model_registry()
    model_entry = registry.get(model_name, {})
    versions = model_entry.get("versions", {})
    resolved_version = requested_version or model_entry.get("default_version", "")
    version_entry = versions.get(resolved_version, {})

    if resolved_version and not version_entry:
        logger.warning(
            "Model registry entry not found for %s version %s, falling back to env defaults.",
            model_name,
            resolved_version,
        )

    anomaly_threshold = env_anomaly_threshold
    if anomaly_threshold is None:
        anomaly_threshold = version_entry.get("anomaly_threshold", 0.5)

    return {
        "model": model_name,
        "model_version": resolved_version or requested_version or "unversioned",
        "model_registry": env_registry_name or version_entry.get("model_registry", "custom"),
        "weights_sha256": env_weights_sha256 or version_entry.get("weights_sha256", ""),
        "description": version_entry.get("description", ""),
        "anomaly_threshold": float(anomaly_threshold),
        "supported_modalities": version_entry.get("supported_modalities", []),
        "device": version_entry.get("device", "cpu"),
    }
