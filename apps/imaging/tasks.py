import logging
import os
import time

from celery import chain, shared_task
from django.utils import timezone

from apps.ai_engine.mongo import store_processing_log
from apps.ai_engine.service import AIServiceRequestError, request_inference
from apps.imaging.models import MedicalImage
from apps.imaging.storage import S3StorageService, StorageError

logger = logging.getLogger(__name__)
IMAGE_PROCESSING_MAX_ATTEMPTS = max(1, int(os.getenv("IMAGE_PROCESSING_MAX_ATTEMPTS", "3")))
IMAGE_PROCESSING_RETRY_BACKOFF_SECONDS = float(
    os.getenv("IMAGE_PROCESSING_RETRY_BACKOFF_SECONDS", "2")
)


def _log_processing_event(
    image_id: str,
    stage: str,
    status: str,
    details: dict | None = None,
) -> None:
    try:
        store_processing_log(image_id, stage, status, details)
    except Exception:
        logger.exception("Failed to store processing log for %s at stage %s", image_id, stage)


def _update_image_metadata(
    image: MedicalImage,
    *,
    status: str | None = None,
    metadata_updates: dict | None = None,
    metadata_remove_keys: list[str] | None = None,
) -> None:
    image.metadata = {**image.metadata, **(metadata_updates or {})}
    for key in metadata_remove_keys or []:
        image.metadata.pop(key, None)
    update_fields = ["metadata"]
    if status is not None:
        image.status = status
        update_fields.append("status")
    image.save(update_fields=update_fields)


def _mark_processing_failure(
    image: MedicalImage,
    *,
    stage: str,
    attempt: int,
    error: Exception,
) -> None:
    _update_image_metadata(
        image,
        status=str(MedicalImage.Status.FAILED),
        metadata_updates={
            "processing_attempts": attempt,
            "processing_error": str(error),
            "processing_failed_at": timezone.now().isoformat(),
        },
    )
    _log_processing_event(
        str(image.id),
        stage,
        "failed",
        {"attempt": attempt, "error": str(error)},
    )
    logger.exception("Image processing failed for image %s", image.id)


@shared_task
def preprocess_image_task(image_id: str) -> str | None:
    image = MedicalImage.objects.filter(id=image_id).first()
    if not image:
        return None
    started_at = time.perf_counter()
    _log_processing_event(image_id, "preprocess", "started")
    _update_image_metadata(
        image,
        status=str(MedicalImage.Status.PROCESSING),
        metadata_updates={"preprocess_started_at": timezone.now().isoformat()},
    )
    _update_image_metadata(
        image,
        metadata_updates={
            "preprocess_completed_at": timezone.now().isoformat(),
            "preprocess_duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
        },
    )
    _log_processing_event(image_id, "preprocess", "completed")
    return str(image.id)


@shared_task
def ai_inference_task(image_id: str) -> None:
    image = MedicalImage.objects.filter(id=image_id).first()
    if not image:
        return
    storage = S3StorageService()
    for attempt in range(1, IMAGE_PROCESSING_MAX_ATTEMPTS + 1):
        started_at = time.perf_counter()
        _log_processing_event(
            image_id,
            "inference",
            "started",
            {"attempt": attempt, "max_attempts": IMAGE_PROCESSING_MAX_ATTEMPTS},
        )
        _update_image_metadata(
            image,
            status=str(MedicalImage.Status.PROCESSING),
            metadata_updates={
                "processing_attempts": attempt,
                "inference_started_at": timezone.now().isoformat(),
            },
        )
        try:
            image_bytes = storage.download(image.s3_key)
            result = request_inference(image_bytes, str(image.id))
        except (AIServiceRequestError, StorageError) as exc:
            retry_in_seconds = round(
                IMAGE_PROCESSING_RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1)),
                2,
            )
            _update_image_metadata(
                image,
                metadata_updates={
                    "processing_attempts": attempt,
                    "last_processing_error": str(exc),
                },
            )
            if attempt < IMAGE_PROCESSING_MAX_ATTEMPTS:
                _log_processing_event(
                    image_id,
                    "inference",
                    "retrying",
                    {
                        "attempt": attempt,
                        "max_attempts": IMAGE_PROCESSING_MAX_ATTEMPTS,
                        "retry_in_seconds": retry_in_seconds,
                        "error": str(exc),
                    },
                )
                time.sleep(retry_in_seconds)
                continue
            _mark_processing_failure(image, stage="inference", attempt=attempt, error=exc)
            return
        except Exception as exc:
            _mark_processing_failure(image, stage="inference", attempt=attempt, error=exc)
            return

        _update_image_metadata(
            image,
            status=str(MedicalImage.Status.PROCESSED),
            metadata_updates={
                "processing_attempts": attempt,
                "ai_model": result.get("model", ""),
                "ai_model_version": result.get("model_version", ""),
                "ai_model_registry": result.get("model_registry", ""),
                "ai_weights_sha256": result.get("weights_sha256", ""),
                "ai_device": result.get("device", ""),
                "ai_service_processing_ms": result.get("service_processing_ms"),
                "image_sha256": result.get("input_sha256", image.metadata.get("stored_sha256", "")),
                "inference_completed_at": timezone.now().isoformat(),
                "inference_duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
            },
            metadata_remove_keys=["processing_error", "last_processing_error"],
        )
        _log_processing_event(
            image_id,
            "inference",
            "completed",
            {
                "attempt": attempt,
                "anomaly_probability": result.get("anomaly_probability"),
                "model": result.get("model"),
                "model_version": result.get("model_version"),
                "model_registry": result.get("model_registry"),
                "service_processing_ms": result.get("service_processing_ms"),
            },
        )
        return


def queue_image_processing(image_id: str):
    return chain(preprocess_image_task.s(image_id), ai_inference_task.s())()
