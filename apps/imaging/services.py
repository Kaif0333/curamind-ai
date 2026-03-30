from __future__ import annotations

import hashlib
import logging
import os
from io import BytesIO

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest

from apps.ai_engine.mongo import store_image_metadata, store_processing_log
from apps.audit_logs.utils import log_action
from apps.authentication.models import User
from apps.imaging.models import MedicalImage
from apps.imaging.storage import S3StorageService, StorageError
from apps.imaging.tasks import queue_image_processing
from apps.imaging.utils import (
    deidentify_dicom_bytes,
    is_dicom_upload,
    validate_upload,
)

logger = logging.getLogger(__name__)

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "100"))


def handle_image_upload(
    user: User,
    upload: UploadedFile,
    request: HttpRequest | None = None,
    modality: str = "",
) -> MedicalImage:
    validate_upload(upload.name, upload.content_type or "", upload.size, MAX_UPLOAD_MB)
    patient_profile = getattr(user, "patient_profile", None)
    if patient_profile is None:
        raise ValueError("Patient profile not found for the uploading user.")

    file_bytes = upload.read()
    metadata: dict[str, str] = {
        "upload_sha256": hashlib.sha256(file_bytes).hexdigest(),
        "original_content_type": upload.content_type or "application/octet-stream",
    }
    resolved_modality = modality
    dicom_upload = is_dicom_upload(upload.name, upload.content_type or "")

    if dicom_upload:
        file_bytes, dicom_metadata = deidentify_dicom_bytes(file_bytes)
        metadata.update(dicom_metadata)
        resolved_modality = metadata.get("Modality", modality)

    metadata["stored_sha256"] = hashlib.sha256(file_bytes).hexdigest()

    storage = S3StorageService()
    key = storage.build_key(upload.name)
    try:
        stored_key = storage.upload(BytesIO(file_bytes), key)
    except StorageError as exc:
        logger.exception("Failed to store image %s", upload.name)
        raise ValueError("Unable to store the uploaded image right now.") from exc

    image = MedicalImage.objects.create(
        patient=patient_profile,
        uploaded_by=user,
        file_name=upload.name,
        s3_key=stored_key,
        modality=resolved_modality,
        content_type=upload.content_type or "application/octet-stream",
        file_size=upload.size,
        metadata=metadata,
        status=MedicalImage.Status.UPLOADED,
    )

    try:
        store_processing_log(
            str(image.id),
            "upload",
            "completed",
            {
                "file_name": image.file_name,
                "modality": resolved_modality,
                "content_type": image.content_type,
                "upload_sha256": metadata.get("upload_sha256"),
            },
        )
    except Exception:
        logger.exception("Failed to store upload processing log for image %s", image.id)

    if dicom_upload:
        try:
            store_processing_log(
                str(image.id),
                "deidentify",
                "completed",
                {"stripped_tags": metadata.get("_stripped_tags", "")},
            )
        except Exception:
            logger.exception("Failed to store deidentify log for image %s", image.id)

    if metadata:
        try:
            store_image_metadata(str(image.id), metadata)
        except Exception:
            logger.exception("Failed to store metadata for image %s", image.id)

    if not settings.CELERY_TASK_ALWAYS_EAGER:
        try:
            queue_image_processing(str(image.id))
        except Exception:
            try:
                store_processing_log(
                    str(image.id),
                    "queue",
                    "failed",
                    {"reason": "Failed to enqueue background processing"},
                )
            except Exception:
                logger.exception("Failed to store queue failure log for image %s", image.id)
            logger.exception("Failed to enqueue background processing for image %s", image.id)
        else:
            try:
                store_processing_log(str(image.id), "queue", "queued")
            except Exception:
                logger.exception("Failed to store queue log for image %s", image.id)

    log_action(user, "image_upload", request, resource_id=str(image.id))
    return image
