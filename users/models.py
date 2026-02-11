from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ("patient", "Patient"),
        ("doctor", "Doctor"),
    )

    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        default="patient"
    )

    def __str__(self):
        return self.username


class Appointment(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )

    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="patient_appointments"
    )

    doctor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="doctor_appointments"
    )

    date = models.DateField()
    time = models.TimeField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient} -> {self.doctor} ({self.status})"
