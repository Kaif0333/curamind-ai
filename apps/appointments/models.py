from __future__ import annotations

import uuid

from django.db import models

from apps.doctors.models import DoctorProfile
from apps.patients.models import PatientProfile


class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        PatientProfile, on_delete=models.CASCADE, related_name="appointments"
    )
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name="appointments")
    scheduled_time = models.DateTimeField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-scheduled_time"]

    def __str__(self) -> str:
        return f"Appointment({self.patient.user.email} -> {self.doctor.user.email})"
