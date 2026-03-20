from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.appointments.models import Appointment
from apps.authentication.models import User
from apps.doctors.models import DoctorProfile
from apps.imaging.models import MedicalImage
from apps.medical_records.models import MedicalRecord
from apps.patients.models import PatientProfile


@pytest.mark.django_db
def test_patient_can_view_own_profile():
    user = User.objects.create_user(
        email="profile-patient@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    PatientProfile.objects.create(user=user, phone="1234567890")

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get("/patients/me")

    assert response.status_code == 200
    assert str(response.data["user"]) == str(user.id)
    assert response.data["phone"] == "1234567890"


@pytest.mark.django_db
def test_doctor_can_view_unique_assigned_patients():
    patient_user = User.objects.create_user(
        email="doctor-patient@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    patient_profile = PatientProfile.objects.create(user=patient_user)

    doctor_user = User.objects.create_user(
        email="doctor-patients@example.com",
        password="StrongPass123",
        role=User.Role.DOCTOR,
    )
    doctor_profile = DoctorProfile.objects.create(user=doctor_user, specialty="Cardiology")
    Appointment.objects.create(
        patient=patient_profile,
        doctor=doctor_profile,
        scheduled_time="2030-01-01T10:00:00Z",
        reason="Initial consult",
    )
    Appointment.objects.create(
        patient=patient_profile,
        doctor=doctor_profile,
        scheduled_time="2030-01-02T10:00:00Z",
        reason="Follow-up",
    )

    client = APIClient()
    client.force_authenticate(user=doctor_user)
    response = client.get("/doctor/patients")

    assert response.status_code == 200
    assert len(response.data) == 1
    assert str(response.data[0]["user"]) == str(patient_user.id)


@pytest.mark.django_db
def test_patient_can_view_ai_result_for_own_image(monkeypatch):
    patient_user = User.objects.create_user(
        email="ai-result-patient@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    patient_profile = PatientProfile.objects.create(user=patient_user)
    image = MedicalImage.objects.create(
        patient=patient_profile,
        uploaded_by=patient_user,
        file_name="result.png",
        s3_key="medical-images/result.png",
        modality="MRI",
        content_type="image/png",
        file_size=123,
        metadata={},
    )

    monkeypatch.setattr(
        "apps.ai_engine.views.get_ai_result_by_image",
        lambda image_id: {
            "image_id": image_id,
            "result": {
                "anomaly_probability": 0.42,
                "heatmap": "abc",
                "model": "resnet50",
            },
        },
    )

    client = APIClient()
    client.force_authenticate(user=patient_user)
    response = client.get(f"/ai/result?image_id={image.id}")

    assert response.status_code == 200
    assert response.data["anomaly_probability"] == 0.42


@pytest.mark.django_db
def test_ai_result_requires_image_id():
    user = User.objects.create_user(
        email="ai-missing-id@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    PatientProfile.objects.create(user=user)

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get("/ai/result")

    assert response.status_code == 400


@pytest.mark.django_db
def test_doctor_cannot_view_unassigned_patient_image_logs():
    patient_user = User.objects.create_user(
        email="image-logs-patient@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    patient_profile = PatientProfile.objects.create(user=patient_user)
    image = MedicalImage.objects.create(
        patient=patient_profile,
        uploaded_by=patient_user,
        file_name="secret.png",
        s3_key="medical-images/secret.png",
        modality="CT",
        content_type="image/png",
        file_size=456,
        metadata={},
    )

    doctor_user = User.objects.create_user(
        email="unassigned-doctor@example.com",
        password="StrongPass123",
        role=User.Role.DOCTOR,
    )
    DoctorProfile.objects.create(user=doctor_user, specialty="Neurology")

    client = APIClient()
    client.force_authenticate(user=doctor_user)
    response = client.get(f"/ai/logs?image_id={image.id}")

    assert response.status_code == 404


@pytest.mark.django_db
def test_doctor_can_view_assigned_patient_image_logs(monkeypatch):
    patient_user = User.objects.create_user(
        email="image-logs-owner@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    patient_profile = PatientProfile.objects.create(user=patient_user)
    doctor_user = User.objects.create_user(
        email="assigned-doctor@example.com",
        password="StrongPass123",
        role=User.Role.DOCTOR,
    )
    doctor_profile = DoctorProfile.objects.create(user=doctor_user, specialty="Radiology")
    Appointment.objects.create(
        patient=patient_profile,
        doctor=doctor_profile,
        scheduled_time="2030-01-01T10:00:00Z",
        reason="Image review",
    )
    image = MedicalImage.objects.create(
        patient=patient_profile,
        uploaded_by=patient_user,
        file_name="shared.png",
        s3_key="medical-images/shared.png",
        modality="X-Ray",
        content_type="image/png",
        file_size=789,
        metadata={},
    )

    monkeypatch.setattr(
        "apps.ai_engine.views.get_processing_logs_by_image",
        lambda image_id: [{"image_id": image_id, "stage": "inference", "status": "completed"}],
    )

    client = APIClient()
    client.force_authenticate(user=doctor_user)
    response = client.get(f"/ai/logs?image_id={image.id}")

    assert response.status_code == 200
    assert response.data[0]["stage"] == "inference"


@pytest.mark.django_db
def test_doctor_can_create_medical_record_for_assigned_patient():
    patient_user = User.objects.create_user(
        email="assigned-record-patient@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    patient_profile = PatientProfile.objects.create(user=patient_user)
    doctor_user = User.objects.create_user(
        email="assigned-record-doctor@example.com",
        password="StrongPass123",
        role=User.Role.DOCTOR,
    )
    doctor_profile = DoctorProfile.objects.create(user=doctor_user, specialty="Family Medicine")
    Appointment.objects.create(
        patient=patient_profile,
        doctor=doctor_profile,
        scheduled_time="2030-01-01T10:00:00Z",
        reason="General review",
    )

    client = APIClient()
    client.force_authenticate(user=doctor_user)
    response = client.post(
        "/records/create",
        {"patient_id": str(patient_profile.id), "diagnosis_text": "Routine check"},
        format="json",
    )

    assert response.status_code == 201
    assert MedicalRecord.objects.filter(doctor=doctor_profile, patient=patient_profile).exists()
