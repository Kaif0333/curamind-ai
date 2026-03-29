from __future__ import annotations

import base64

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.appointments.models import Appointment
from apps.audit_logs.models import AuditLog
from apps.authentication.models import User
from apps.doctors.models import DoctorProfile
from apps.medical_records.models import Diagnosis, MedicalRecord, Prescription
from apps.patients.models import PatientProfile
from apps.reports.models import Report


@pytest.mark.django_db
def test_end_to_end_api_workflow_across_patient_doctor_and_radiologist(monkeypatch):
    monkeypatch.setattr(
        "apps.appointments.views.send_email_notification.delay",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "apps.reports.views.send_email_notification.delay",
        lambda *args, **kwargs: None,
    )

    patient_user = User.objects.create_user(
        email="workflow-patient@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    patient_profile = PatientProfile.objects.create(user=patient_user)
    doctor_user = User.objects.create_user(
        email="workflow-doctor@example.com",
        password="StrongPass123",
        role=User.Role.DOCTOR,
    )
    doctor_profile = DoctorProfile.objects.create(user=doctor_user, specialty="Radiology")
    radiologist_user = User.objects.create_user(
        email="workflow-radiologist@example.com",
        password="StrongPass123",
        role=User.Role.RADIOLOGIST,
    )
    DoctorProfile.objects.create(user=radiologist_user, specialty="Radiology")
    admin_user = User.objects.create_user(
        email="workflow-admin@example.com",
        password="StrongPass123",
        role=User.Role.ADMIN,
        is_staff=True,
    )

    patient_client = APIClient()
    patient_client.force_authenticate(user=patient_user)

    appointment_response = patient_client.post(
        "/appointments",
        {
            "doctor_id": str(doctor_profile.id),
            "scheduled_time": "2030-01-01T10:00:00Z",
            "reason": "End-to-end review",
        },
        format="json",
    )
    assert appointment_response.status_code == 201
    appointment_id = appointment_response.data["id"]

    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lE"
        "QVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
    )
    upload = SimpleUploadedFile("workflow.png", png_bytes, content_type="image/png")
    upload_response = patient_client.post(
        "/upload-image",
        {"file": upload, "modality": "X-Ray"},
        format="multipart",
    )
    assert upload_response.status_code == 201
    image_id = upload_response.data["id"]

    doctor_client = APIClient()
    doctor_client.force_authenticate(user=doctor_user)

    doctor_patients_response = doctor_client.get("/doctor/patients")
    assert doctor_patients_response.status_code == 200
    assert doctor_patients_response.data[0]["id"] == str(patient_profile.id)

    appointment_update_response = doctor_client.patch(
        f"/appointments/{appointment_id}/status",
        {"status": Appointment.Status.APPROVED},
        format="json",
    )
    assert appointment_update_response.status_code == 200

    record_response = doctor_client.post(
        "/records/create",
        {
            "patient_id": str(patient_profile.id),
            "diagnosis_text": "Workflow diagnosis",
            "ai_analysis": {"triage": "review"},
        },
        format="json",
    )
    assert record_response.status_code == 201
    record_id = record_response.data["id"]

    diagnosis_response = doctor_client.post(
        f"/records/{record_id}/diagnoses",
        {"text": "Follow-up diagnosis"},
        format="json",
    )
    prescription_response = doctor_client.post(
        f"/records/{record_id}/prescriptions",
        {
            "medication_name": "Ibuprofen",
            "dosage": "200mg",
            "instructions": "After meals",
        },
        format="json",
    )
    report_response = doctor_client.post(
        "/reports/create",
        {"medical_record_id": record_id, "content": "Workflow report draft"},
        format="json",
    )

    assert diagnosis_response.status_code == 201
    assert prescription_response.status_code == 201
    assert report_response.status_code == 201
    report_id = report_response.data["id"]

    monkeypatch.setattr(
        "apps.ai_engine.views.get_ai_result_by_image",
        lambda requested_image_id: (
            {
                "image_id": requested_image_id,
                "result": {
                    "anomaly_probability": 0.17,
                    "heatmap": "workflow-heatmap",
                    "model": "resnet50",
                    "model_version": "demo-resnet50-v1",
                    "device": "cpu",
                },
            }
            if requested_image_id == image_id
            else None
        ),
    )

    ai_result_response = patient_client.get("/ai/result", {"image_id": image_id})
    assert ai_result_response.status_code == 200
    assert ai_result_response.data["model_version"] == "demo-resnet50-v1"
    assert ai_result_response.data["device"] == "cpu"

    radiologist_client = APIClient()
    radiologist_client.force_authenticate(user=radiologist_user)

    radiologist_reports_response = radiologist_client.get("/reports")
    approve_response = radiologist_client.patch(
        f"/reports/{report_id}/approve",
        {"approve": True},
        format="json",
    )

    assert radiologist_reports_response.status_code == 200
    assert any(report["id"] == report_id for report in radiologist_reports_response.data)
    assert approve_response.status_code == 200

    patient_records_response = patient_client.get("/patient/records")
    patient_reports_response = patient_client.get("/reports")
    report_download_response = patient_client.get(f"/reports/{report_id}/download")

    assert patient_records_response.status_code == 200
    assert patient_reports_response.status_code == 200
    assert len(patient_reports_response.data) == 1
    assert report_download_response.status_code == 200
    assert b"Workflow report draft" in report_download_response.content

    admin_client = APIClient()
    admin_client.force_authenticate(user=admin_user)
    audit_response = admin_client.get("/audit-logs", {"resource_id": report_id})

    assert audit_response.status_code == 200
    audit_actions = {entry["action"] for entry in audit_response.data}
    assert {"report_create", "report_approve"} <= audit_actions

    assert MedicalRecord.objects.filter(id=record_id).exists()
    assert Diagnosis.objects.filter(medical_record_id=record_id).exists()
    assert Prescription.objects.filter(medical_record_id=record_id).exists()
    assert Report.objects.filter(id=report_id, status=Report.Status.APPROVED).exists()
    assert AuditLog.objects.filter(resource_id=report_id, action="report_download").exists()
