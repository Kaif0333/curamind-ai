from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.utils import timezone


USER_TYPE_CHOICES = (
    ('doctor', 'Doctor'),
    ('patient', 'Patient'),
)


class UserManager(DjangoUserManager):
    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields['user_type'] = extra_fields.get('user_type') or 'patient'
        return super().create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields['user_type'] = extra_fields.get('user_type') or 'patient'
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    USER_TYPE_CHOICES = USER_TYPE_CHOICES

    user_type = models.CharField(
        max_length=10,
        choices=USER_TYPE_CHOICES,
        default='patient',
    )
    objects = UserManager()

    def clean(self):
        if not self.user_type:
            self.user_type = 'patient'
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['doctor', 'date', 'time'],
                condition=Q(status__in=['pending', 'approved']),
                name='uniq_active_doctor_slot',
            ),
        ]

    def clean(self):
        errors = {}
        if self.patient_id and self.patient.user_type != 'patient':
            errors['patient'] = 'Selected patient account must have patient role.'
        if self.doctor_id and self.doctor.user_type != 'doctor':
            errors['doctor'] = 'Selected doctor account must have doctor role.'
        if self.patient_id and self.doctor_id and self.patient_id == self.doctor_id:
            errors['doctor'] = 'Doctor and patient must be different users.'
        if self._state.adding and self.date and self.date < timezone.localdate():
            errors['date'] = 'Appointment date cannot be in the past.'
        if self.doctor_id and self.date and self.time and self.status in ['pending', 'approved']:
            overlapping = Appointment.objects.filter(
                doctor_id=self.doctor_id,
                date=self.date,
                time=self.time,
                status__in=['pending', 'approved'],
            )
            if self.pk:
                overlapping = overlapping.exclude(pk=self.pk)
            if overlapping.exists():
                errors['time'] = 'This doctor already has an appointment for that slot.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.patient} -> {self.doctor} ({self.status})"
