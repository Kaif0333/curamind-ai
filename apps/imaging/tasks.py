import logging

from celery import chain, shared_task

from apps.ai_engine.mongo import store_processing_log
from apps.ai_engine.service import request_inference
from apps.imaging.models import MedicalImage
from apps.imaging.storage import S3StorageService

logger = logging.getLogger(__name__)


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


@shared_task
def preprocess_image_task(image_id: str) -> str | None:
    image = MedicalImage.objects.filter(id=image_id).first()
    if not image:
        return None
    _log_processing_event(image_id, "preprocess", "started")
    image.status = MedicalImage.Status.PROCESSING
    image.save(update_fields=["status"])
    _log_processing_event(image_id, "preprocess", "completed")
    return str(image.id)


@shared_task
def ai_inference_task(image_id: str) -> None:
    image = MedicalImage.objects.filter(id=image_id).first()
    if not image:
        return
    _log_processing_event(image_id, "inference", "started")
    image.status = MedicalImage.Status.PROCESSING
    image.save(update_fields=["status"])
    storage = S3StorageService()
    try:
        image_bytes = storage.download(image.s3_key)
        result = request_inference(image_bytes, str(image.id))
    except Exception as exc:
        image.status = MedicalImage.Status.FAILED
        image.metadata = {**image.metadata, "processing_error": str(exc)}
        image.save(update_fields=["status", "metadata"])
        _log_processing_event(
            image_id,
            "inference",
            "failed",
            {"error": str(exc)},
        )
        logger.exception("AI inference failed for image %s", image.id)
        return

    image.status = MedicalImage.Status.PROCESSED
    image.save(update_fields=["status"])
    _log_processing_event(
        image_id,
        "inference",
        "completed",
        {"anomaly_probability": result.get("anomaly_probability")},
    )


def queue_image_processing(image_id: str) -> None:
    chain(preprocess_image_task.s(image_id), ai_inference_task.s())()
