from celery import shared_task

from apps.ai_engine.service import request_inference
from apps.imaging.models import MedicalImage
from apps.imaging.storage import S3StorageService


@shared_task
def preprocess_image_task(image_id: str) -> None:
    image = MedicalImage.objects.filter(id=image_id).first()
    if not image:
        return
    image.status = MedicalImage.Status.PROCESSING
    image.save(update_fields=["status"])


@shared_task
def ai_inference_task(image_id: str) -> None:
    image = MedicalImage.objects.filter(id=image_id).first()
    if not image:
        return
    storage = S3StorageService()
    image_bytes = storage.download(image.s3_key)
    request_inference(image_bytes, str(image.id))
    image.status = MedicalImage.Status.PROCESSED
    image.save(update_fields=["status"])
