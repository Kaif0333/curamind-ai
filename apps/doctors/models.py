from __future__ import annotations

import uuid

from django.db import models

from apps.authentication.models import User


class DoctorProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="doctor_profile")
    specialty = models.CharField(max_length=128, blank=True)
    license_number = models.CharField(max_length=64, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    department = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"DoctorProfile({self.user.email})"
