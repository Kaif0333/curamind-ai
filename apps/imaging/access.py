from __future__ import annotations

from apps.appointments.models import Appointment
from apps.authentication.models import User
from apps.imaging.models import MedicalImage
from apps.medical_records.models import MedicalRecord


def get_authorized_image_for_user(user, image_id: str) -> MedicalImage | None:
    if not user or not user.is_authenticated:
        return None

    image = MedicalImage.objects.filter(id=image_id).select_related("patient__user").first()
    if not image:
        return None

    if user.role == User.Role.PATIENT:
        return image if image.patient.user == user else None

    if user.role == User.Role.DOCTOR:
        doctor_profile = getattr(user, "doctor_profile", None)
        if not doctor_profile:
            return None
        is_assigned_patient = (
            Appointment.objects.filter(doctor=doctor_profile, patient=image.patient).exists()
            or MedicalRecord.objects.filter(doctor=doctor_profile, patient=image.patient).exists()
        )
        return image if is_assigned_patient else None

    if user.role == User.Role.NURSE:
        return None

    return image
