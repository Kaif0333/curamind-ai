from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError


class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('doctor', 'Doctor'),
        ('patient', 'Patient'),
    )

    user_type = models.CharField(
        max_length=10,
        choices=USER_TYPE_CHOICES
    )

    def __str__(self):
        return self.username


class Appointment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='patient_appointments',
        limit_choices_to={'user_type': 'patient'},
    )
    doctor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='doctor_appointments',
        limit_choices_to={'user_type': 'doctor'},
    )
    date = models.DateField()
    time = models.TimeField()
    description = models.TextField(blank=True)

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending'
    )

    def clean(self):
        errors = {}
        if self.patient_id and self.patient.user_type != 'patient':
            errors['patient'] = 'Selected patient account must have patient role.'
        if self.doctor_id and self.doctor.user_type != 'doctor':
            errors['doctor'] = 'Selected doctor account must have doctor role.'
        if self.patient_id and self.doctor_id and self.patient_id == self.doctor_id:
            errors['doctor'] = 'Doctor and patient must be different users.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.patient} → {self.doctor} ({self.status})"
