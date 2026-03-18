from __future__ import annotations

import uuid

from django.db import models

from apps.doctors.models import DoctorProfile
from apps.patients.models import PatientProfile


class MedicalRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        PatientProfile, on_delete=models.CASCADE, related_name="medical_records"
    )
    doctor = models.ForeignKey(
        DoctorProfile, on_delete=models.CASCADE, related_name="medical_records"
    )
    diagnosis_text = models.TextField()
    ai_analysis = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"MedicalRecord({self.patient.user.email})"


class Diagnosis(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    medical_record = models.ForeignKey(
        MedicalRecord, on_delete=models.CASCADE, related_name="diagnoses"
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class Prescription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    medical_record = models.ForeignKey(
        MedicalRecord, on_delete=models.CASCADE, related_name="prescriptions"
    )
    medication_name = models.CharField(max_length=128)
    dosage = models.CharField(max_length=64)
    instructions = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
