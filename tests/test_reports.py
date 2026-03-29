import pytest
from rest_framework.test import APIClient

from apps.appointments.models import Appointment
from apps.authentication.models import User
from apps.doctors.models import DoctorProfile
from apps.medical_records.models import MedicalRecord
from apps.patients.models import PatientProfile
from apps.reports.models import Report


@pytest.mark.django_db
def test_radiologist_can_list_reports():
    patient_user = User.objects.create_user(
        email="report-patient@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    patient_profile = PatientProfile.objects.create(user=patient_user)

    doctor_user = User.objects.create_user(
        email="report-doctor@example.com",
        password="StrongPass123",
        role=User.Role.DOCTOR,
    )
    doctor_profile = DoctorProfile.objects.create(user=doctor_user, specialty="Cardiology")
    Appointment.objects.create(
        patient=patient_profile,
        doctor=doctor_profile,
        scheduled_time="2030-01-01T10:00:00Z",
        reason="Checkup",
    )
    record = MedicalRecord.objects.create(
        patient=patient_profile,
        doctor=doctor_profile,
        diagnosis_text="Demo diagnosis",
    )
    report = Report.objects.create(
        medical_record=record,
        author=doctor_user,
        status=Report.Status.DRAFT,
        content="Draft report",
    )

    radiologist_user = User.objects.create_user(
        email="report-radiologist@example.com",
        password="StrongPass123",
        role=User.Role.RADIOLOGIST,
    )
    DoctorProfile.objects.create(user=radiologist_user, specialty="Radiology")

    client = APIClient()
    client.force_authenticate(user=radiologist_user)
    response = client.get("/reports")

    assert response.status_code == 200
    assert [item["id"] for item in response.data] == [str(report.id)]


@pytest.mark.django_db
def test_doctor_cannot_create_report_for_foreign_record():
    patient_user = User.objects.create_user(
        email="foreign-patient@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    patient_profile = PatientProfile.objects.create(user=patient_user)

    owner_user = User.objects.create_user(
        email="owner-doctor@example.com",
        password="StrongPass123",
        role=User.Role.DOCTOR,
    )
    owner_profile = DoctorProfile.objects.create(user=owner_user, specialty="Cardiology")
    Appointment.objects.create(
        patient=patient_profile,
        doctor=owner_profile,
        scheduled_time="2030-01-01T10:00:00Z",
        reason="Checkup",
    )
    record = MedicalRecord.objects.create(
        patient=patient_profile,
        doctor=owner_profile,
        diagnosis_text="Private diagnosis",
    )

    other_user = User.objects.create_user(
        email="other-doctor@example.com",
        password="StrongPass123",
        role=User.Role.DOCTOR,
    )
    DoctorProfile.objects.create(user=other_user, specialty="Neurology")

    client = APIClient()
    client.force_authenticate(user=other_user)
    response = client.post(
        "/reports/create",
        {"medical_record_id": str(record.id), "content": "Unauthorized report"},
        format="json",
    )

    assert response.status_code == 403
    assert Report.objects.count() == 0


@pytest.mark.django_db
def test_patient_can_download_approved_report_but_not_draft():
    patient_user = User.objects.create_user(
        email="download-patient@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    patient_profile = PatientProfile.objects.create(user=patient_user)

    doctor_user = User.objects.create_user(
        email="download-doctor@example.com",
        password="StrongPass123",
        role=User.Role.DOCTOR,
    )
    doctor_profile = DoctorProfile.objects.create(user=doctor_user, specialty="Radiology")
    record = MedicalRecord.objects.create(
        patient=patient_profile,
        doctor=doctor_profile,
        diagnosis_text="Imaging follow-up",
    )
    approved_report = Report.objects.create(
        medical_record=record,
        author=doctor_user,
        status=Report.Status.APPROVED,
        content="Approved report content",
    )
    draft_report = Report.objects.create(
        medical_record=record,
        author=doctor_user,
        status=Report.Status.DRAFT,
        content="Draft report content",
    )

    client = APIClient()
    client.force_authenticate(user=patient_user)

    approved_response = client.get(f"/reports/{approved_report.id}/download")
    draft_response = client.get(f"/reports/{draft_report.id}/download")

    assert approved_response.status_code == 200
    assert "Approved report content" in approved_response.content.decode("utf-8")
    assert draft_response.status_code == 404


@pytest.mark.django_db
def test_admin_cannot_download_private_patient_report():
    patient_user = User.objects.create_user(
        email="download-admin-patient@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    patient_profile = PatientProfile.objects.create(user=patient_user)

    doctor_user = User.objects.create_user(
        email="download-admin-doctor@example.com",
        password="StrongPass123",
        role=User.Role.DOCTOR,
    )
    doctor_profile = DoctorProfile.objects.create(user=doctor_user, specialty="Radiology")
    record = MedicalRecord.objects.create(
        patient=patient_profile,
        doctor=doctor_profile,
        diagnosis_text="Protected report",
    )
    report = Report.objects.create(
        medical_record=record,
        author=doctor_user,
        status=Report.Status.APPROVED,
        content="Sensitive report content",
    )

    admin_user = User.objects.create_user(
        email="download-admin@example.com",
        password="StrongPass123",
        role=User.Role.ADMIN,
        is_staff=True,
    )

    client = APIClient()
    client.force_authenticate(user=admin_user)

    response = client.get(f"/reports/{report.id}/download")

    assert response.status_code == 403
