from __future__ import annotations

import pytest

from apps.appointments.models import Appointment
from apps.authentication.models import LoginAttempt, User
from apps.doctors.models import DoctorProfile
from apps.imaging.models import MedicalImage
from apps.imaging.serializers import MedicalImageSerializer
from apps.medical_records.models import MedicalRecord
from apps.patients.models import PatientProfile
from apps.reports.models import Report


@pytest.mark.django_db
def test_model_string_helpers_and_image_download_url():
    patient_user = User.objects.create_user(
        email="helper-patient@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    patient_profile = PatientProfile.objects.create(user=patient_user)
    doctor_user = User.objects.create_user(
        email="helper-doctor@example.com",
        password="StrongPass123",
        role=User.Role.DOCTOR,
    )
    doctor_profile = DoctorProfile.objects.create(user=doctor_user, specialty="Radiology")

    appointment = Appointment.objects.create(
        patient=patient_profile,
        doctor=doctor_profile,
        scheduled_time="2030-01-01T10:00:00Z",
        reason="Helper check",
    )
    record = MedicalRecord.objects.create(
        patient=patient_profile,
        doctor=doctor_profile,
        diagnosis_text="Helper diagnosis",
    )
    report = Report.objects.create(
        medical_record=record,
        author=doctor_user,
        status=Report.Status.DRAFT,
        content="Helper report",
    )
    image = MedicalImage.objects.create(
        patient=patient_profile,
        uploaded_by=patient_user,
        file_name="helper.png",
        s3_key="medical-images/helper.png",
        modality="MRI",
        content_type="image/png",
        file_size=123,
        metadata={},
    )
    attempt = LoginAttempt.objects.create(
        user=patient_user,
        email=patient_user.email,
        success=False,
    )

    serialized_image = MedicalImageSerializer(image).data

    assert "Appointment(" in str(appointment)
    assert str(record) == f"MedicalRecord({patient_user.email})"
    assert str(report) == f"Report({report.id})"
    assert str(image) == "MedicalImage(helper.png)"
    assert str(patient_profile) == f"PatientProfile({patient_user.email})"
    assert str(doctor_profile) == f"DoctorProfile({doctor_user.email})"
    assert str(attempt) == f"{patient_user.email} - failure"
    assert serialized_image["download_url"].endswith(f"/imaging/{image.id}/download")
