from __future__ import annotations

import uuid

from django.db import models

from apps.authentication.models import User
from apps.medical_records.models import MedicalRecord


class Report(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        APPROVED = "approved", "Approved"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    medical_record = models.ForeignKey(
        MedicalRecord, on_delete=models.CASCADE, related_name="reports"
    )
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="reports")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Report({self.id})"
