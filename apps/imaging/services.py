from __future__ import annotations

import logging
import os
from io import BytesIO

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest

from apps.ai_engine.mongo import store_image_metadata
from apps.audit_logs.utils import log_action
from apps.authentication.models import User
from apps.imaging.models import MedicalImage
from apps.imaging.storage import S3StorageService
from apps.imaging.tasks import queue_image_processing
from apps.imaging.utils import extract_dicom_metadata, is_dicom_upload, validate_upload

logger = logging.getLogger(__name__)

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "100"))


def handle_image_upload(
    user: User,
    upload: UploadedFile,
    request: HttpRequest | None = None,
    modality: str = "",
) -> MedicalImage:
    validate_upload(upload.name, upload.content_type or "", upload.size, MAX_UPLOAD_MB)

    file_bytes = upload.read()
    metadata: dict[str, str] = {}
    resolved_modality = modality

    if is_dicom_upload(upload.name, upload.content_type or ""):
        metadata = extract_dicom_metadata(file_bytes)
        resolved_modality = metadata.get("Modality", modality)

    storage = S3StorageService()
    key = storage.build_key(upload.name)
    stored_key = storage.upload(BytesIO(file_bytes), key)

    image = MedicalImage.objects.create(
        patient=user.patient_profile,
        uploaded_by=user,
        file_name=upload.name,
        s3_key=stored_key,
        modality=resolved_modality,
        content_type=upload.content_type or "application/octet-stream",
        file_size=upload.size,
        metadata=metadata,
        status=MedicalImage.Status.UPLOADED,
    )

    if metadata:
        try:
            store_image_metadata(str(image.id), metadata)
        except Exception:
            logger.exception("Failed to store metadata for image %s", image.id)

    if not settings.CELERY_TASK_ALWAYS_EAGER:
        try:
            queue_image_processing(str(image.id))
        except Exception:
            logger.exception("Failed to enqueue background processing for image %s", image.id)

    log_action(user, "image_upload", request, resource_id=str(image.id))
    return image
