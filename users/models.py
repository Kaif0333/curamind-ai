from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ("doctor", "Doctor"),
        ("patient", "Patient"),
    )

    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES
    )

    def __str__(self):
        return self.username


class Appointment(models.Model):
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
        default="pending"
    )

    def __str__(self):
        return f"{self.patient} → {self.doctor} ({self.status})"
