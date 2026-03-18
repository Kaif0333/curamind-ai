import logging

from celery import chain, shared_task

from apps.ai_engine.service import request_inference
from apps.imaging.models import MedicalImage
from apps.imaging.storage import S3StorageService

logger = logging.getLogger(__name__)


@shared_task
def preprocess_image_task(image_id: str) -> str | None:
    image = MedicalImage.objects.filter(id=image_id).first()
    if not image:
        return None
    image.status = MedicalImage.Status.PROCESSING
    image.save(update_fields=["status"])
    return str(image.id)


@shared_task
def ai_inference_task(image_id: str) -> None:
    image = MedicalImage.objects.filter(id=image_id).first()
    if not image:
        return
    image.status = MedicalImage.Status.PROCESSING
    image.save(update_fields=["status"])
    storage = S3StorageService()
    try:
        image_bytes = storage.download(image.s3_key)
        request_inference(image_bytes, str(image.id))
    except Exception as exc:
        image.status = MedicalImage.Status.FAILED
        image.metadata = {**image.metadata, "processing_error": str(exc)}
        image.save(update_fields=["status", "metadata"])
        logger.exception("AI inference failed for image %s", image.id)
        return

    image.status = MedicalImage.Status.PROCESSED
    image.save(update_fields=["status"])


def queue_image_processing(image_id: str) -> None:
    chain(preprocess_image_task.s(image_id), ai_inference_task.s())()
