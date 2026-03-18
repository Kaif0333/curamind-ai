from __future__ import annotations

import uuid

from django.db import models

from apps.authentication.models import User
from apps.imaging.storage import S3StorageService
from apps.patients.models import PatientProfile


class MedicalImage(models.Model):
    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        PROCESSING = "processing", "Processing"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name="images")
    uploaded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="uploaded_images"
    )
    file_name = models.CharField(max_length=256)
    s3_key = models.CharField(max_length=512)
    modality = models.CharField(max_length=32, blank=True)
    content_type = models.CharField(max_length=128)
    file_size = models.PositiveIntegerField()
    metadata = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.UPLOADED)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"MedicalImage({self.file_name})"

    @property
    def download_url(self) -> str:
        storage = S3StorageService()
        return storage.presigned_url(self.s3_key)
