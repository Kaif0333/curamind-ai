from __future__ import annotations

import pyotp
import pytest
from django.test import Client
from django.urls import reverse

from apps.appointments.models import Appointment
from apps.audit_logs.models import AuditLog
from apps.authentication.models import User
from apps.doctors.models import DoctorProfile
from apps.medical_records.models import Diagnosis, MedicalRecord, Prescription
from apps.patients.models import PatientProfile
from apps.reports.models import Report


@pytest.mark.django_db
def test_portal_login_logout_and_register_flow():
    user = User.objects.create_user(
        email="portal-login-flow@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    PatientProfile.objects.create(user=user)

    client = Client()

    login_response = client.post(
        reverse("portal-login"),
        {"email": user.email, "password": "StrongPass123"},
        follow=False,
    )
    assert login_response.status_code == 302
    assert login_response.url == reverse("portal-dashboard")

    logout_response = client.get(reverse("portal-logout"), follow=False)
    assert logout_response.status_code == 302
    assert logout_response.url == reverse("portal-home")

    register_response = client.post(
        reverse("portal-register"),
        {
            "email": "portal-register@example.com",
            "password": "StrongPass123",
            "first_name": "Portal",
            "last_name": "User",
            "role": User.Role.PATIENT,
        },
        follow=False,
    )
    new_user = User.objects.get(email="portal-register@example.com")

    assert register_response.status_code == 302
    assert register_response.url == reverse("portal-login")
    assert new_user.role == User.Role.PATIENT


@pytest.mark.django_db
def test_portal_register_honors_configured_self_assignable_roles(monkeypatch):
    monkeypatch.setenv("ALLOW_SELF_ASSIGN_ROLES", "true")
    monkeypatch.setenv("SELF_ASSIGNABLE_ROLES", "patient,doctor")

    client = Client()
    response = client.post(
        reverse("portal-register"),
        {
            "email": "portal-doctor-register@example.com",
            "password": "StrongPass123",
            "first_name": "Portal",
            "last_name": "Doctor",
            "role": User.Role.DOCTOR,
        },
        follow=False,
    )

    user = User.objects.get(email="portal-doctor-register@example.com")

    assert response.status_code == 302
    assert user.role == User.Role.DOCTOR
    assert hasattr(user, "doctor_profile")


@pytest.mark.django_db
def test_portal_login_rate_limit_and_missing_mfa_challenge():
    user = User.objects.create_user(
        email="portal-rate-limit@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    PatientProfile.objects.create(user=user)

    client = Client()
    session = client.session
    session["pending_portal_mfa_user_id"] = "missing"
    session.save()

    missing_challenge_response = client.get(reverse("portal-mfa-login"), follow=False)
    assert missing_challenge_response.status_code == 302
    assert missing_challenge_response.url == reverse("portal-login")

    from apps.authentication.views import MAX_LOGIN_ATTEMPTS, _attempt_key
    from django.core.cache import cache

    cache.set(_attempt_key(user.email, "127.0.0.1"), MAX_LOGIN_ATTEMPTS, timeout=60)
    rate_limited_response = client.post(
        reverse("portal-login"),
        {"email": user.email, "password": "StrongPass123"},
        REMOTE_ADDR="127.0.0.1",
    )

    assert rate_limited_response.status_code == 200
    assert b"Too many login attempts" in rate_limited_response.content


@pytest.mark.django_db
def test_portal_mfa_settings_full_flow():
    user = User.objects.create_user(
        email="portal-mfa-settings@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    PatientProfile.objects.create(user=user)

    client = Client()
    client.force_login(user)

    start_response = client.post(
        reverse("portal-mfa-settings"),
        {"action": "start"},
    )
    user.refresh_from_db()

    assert start_response.status_code == 200
    assert user.mfa_secret
    assert user.mfa_enabled is False

    invalid_verify = client.post(
        reverse("portal-mfa-settings"),
        {"action": "verify", "code": "123456"},
    )
    assert invalid_verify.status_code == 200

    valid_code = pyotp.TOTP(user.mfa_secret).now()
    valid_verify = client.post(
        reverse("portal-mfa-settings"),
        {"action": "verify", "code": valid_code},
        follow=False,
    )
    user.refresh_from_db()
    assert valid_verify.status_code == 302
    assert user.mfa_enabled is True

    wrong_disable = client.post(
        reverse("portal-mfa-settings"),
        {"action": "disable", "password": "wrong", "code": valid_code},
    )
    assert wrong_disable.status_code == 200

    disable_code = pyotp.TOTP(user.mfa_secret).now()
    disable_response = client.post(
        reverse("portal-mfa-settings"),
        {"action": "disable", "password": "StrongPass123", "code": disable_code},
        follow=False,
    )
    user.refresh_from_db()

    assert disable_response.status_code == 302
    assert user.mfa_enabled is False
    assert user.mfa_secret == ""


@pytest.mark.django_db
def test_doctor_portal_dashboard_and_actions():
    patient_user = User.objects.create_user(
        email="portal-doctor-patient@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    patient_profile = PatientProfile.objects.create(user=patient_user)

    doctor_user = User.objects.create_user(
        email="portal-doctor-actions@example.com",
        password="StrongPass123",
        role=User.Role.DOCTOR,
    )
    doctor_profile = DoctorProfile.objects.create(user=doctor_user, specialty="Orthopedics")
    appointment = Appointment.objects.create(
        patient=patient_profile,
        doctor=doctor_profile,
        scheduled_time="2030-01-01T10:00:00Z",
        reason="Knee pain",
        status=Appointment.Status.PENDING,
    )

    client = Client()
    client.force_login(doctor_user)

    dashboard_response = client.get(reverse("portal-dashboard"))
    assert dashboard_response.status_code == 200

    update_response = client.post(
        reverse("portal-update-appointment-status", args=[appointment.id]),
        {"status": Appointment.Status.APPROVED},
        follow=False,
    )
    appointment.refresh_from_db()
    assert update_response.status_code == 302
    assert appointment.status == Appointment.Status.APPROVED

    create_record_response = client.post(
        reverse("portal-create-record"),
        {"patient": str(patient_profile.id), "diagnosis_text": "Portal record diagnosis"},
        follow=False,
    )
    record = MedicalRecord.objects.get(patient=patient_profile, doctor=doctor_profile)
    assert create_record_response.status_code == 302

    diagnosis_response = client.post(
        reverse("portal-add-diagnosis"),
        {"medical_record": str(record.id), "text": "Portal diagnosis detail"},
        follow=False,
    )
    prescription_response = client.post(
        reverse("portal-add-prescription"),
        {
            "medical_record": str(record.id),
            "medication_name": "Ibuprofen",
            "dosage": "200mg",
            "instructions": "After meals",
        },
        follow=False,
    )
    report_response = client.post(
        reverse("portal-create-report"),
        {"medical_record": str(record.id), "content": "Portal report draft"},
        follow=False,
    )

    assert diagnosis_response.status_code == 302
    assert prescription_response.status_code == 302
    assert report_response.status_code == 302
    assert Diagnosis.objects.filter(medical_record=record, text__icontains="detail").exists()
    assert Prescription.objects.filter(medical_record=record, medication_name="Ibuprofen").exists()
    assert Report.objects.filter(medical_record=record, author=doctor_user).exists()


@pytest.mark.django_db
def test_portal_doctor_can_create_record_for_patient_already_assigned_by_existing_record_only():
    patient_user = User.objects.create_user(
        email="portal-existing-record-patient@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    patient_profile = PatientProfile.objects.create(user=patient_user)
    doctor_user = User.objects.create_user(
        email="portal-existing-record-doctor@example.com",
        password="StrongPass123",
        role=User.Role.DOCTOR,
    )
    doctor_profile = DoctorProfile.objects.create(user=doctor_user, specialty="General")
    MedicalRecord.objects.create(
        patient=patient_profile,
        doctor=doctor_profile,
        diagnosis_text="Existing doctor assignment",
    )

    client = Client()
    client.force_login(doctor_user)
    response = client.post(
        reverse("portal-create-record"),
        {"patient": str(patient_profile.id), "diagnosis_text": "Follow-up doctor note"},
        follow=False,
    )

    assert response.status_code == 302
    assert MedicalRecord.objects.filter(
        patient=patient_profile,
        doctor=doctor_profile,
        diagnosis_text="Follow-up doctor note",
    ).exists()


@pytest.mark.django_db
def test_radiologist_and_admin_portal_dashboards_and_report_approval():
    patient_user = User.objects.create_user(
        email="portal-rad-patient@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    patient_profile = PatientProfile.objects.create(user=patient_user)

    doctor_user = User.objects.create_user(
        email="portal-rad-doctor@example.com",
        password="StrongPass123",
        role=User.Role.DOCTOR,
    )
    doctor_profile = DoctorProfile.objects.create(user=doctor_user, specialty="Cardiology")
    record = MedicalRecord.objects.create(
        patient=patient_profile,
        doctor=doctor_profile,
        diagnosis_text="Awaiting approval",
    )
    report = Report.objects.create(
        medical_record=record,
        author=doctor_user,
        status=Report.Status.DRAFT,
        content="Draft for approval",
    )

    radiologist_user = User.objects.create_user(
        email="portal-radiologist@example.com",
        password="StrongPass123",
        role=User.Role.RADIOLOGIST,
    )
    DoctorProfile.objects.create(user=radiologist_user, specialty="Radiology")

    client = Client()
    client.force_login(radiologist_user)
    dashboard_response = client.get(reverse("portal-dashboard"))
    approve_response = client.post(
        reverse("portal-approve-report", args=[report.id]),
        {"approve": "on"},
        follow=False,
    )
    report.refresh_from_db()

    assert dashboard_response.status_code == 200
    assert approve_response.status_code == 302
    assert report.status == Report.Status.APPROVED

    admin_user = User.objects.create_user(
        email="portal-admin@example.com",
        password="StrongPass123",
        role=User.Role.ADMIN,
        is_staff=True,
    )
    AuditLog.objects.create(user=doctor_user, action="report_create", resource_id=str(report.id))
    client.force_login(admin_user)
    admin_response = client.get(reverse("portal-dashboard"), {"action": "report_create"})

    assert admin_response.status_code == 200
    assert b"report_create" in admin_response.content


@pytest.mark.django_db
def test_portal_download_permissions_and_not_found_branches():
    patient_user = User.objects.create_user(
        email="portal-download-patient@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    patient_profile = PatientProfile.objects.create(user=patient_user)
    other_patient = User.objects.create_user(
        email="portal-download-other@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    PatientProfile.objects.create(user=other_patient)

    doctor_user = User.objects.create_user(
        email="portal-download-doctor@example.com",
        password="StrongPass123",
        role=User.Role.DOCTOR,
    )
    doctor_profile = DoctorProfile.objects.create(user=doctor_user, specialty="Dermatology")
    foreign_doctor = User.objects.create_user(
        email="portal-download-foreign@example.com",
        password="StrongPass123",
        role=User.Role.DOCTOR,
    )
    DoctorProfile.objects.create(user=foreign_doctor, specialty="Radiology")

    record = MedicalRecord.objects.create(
        patient=patient_profile,
        doctor=doctor_profile,
        diagnosis_text="Download branches",
    )
    approved_report = Report.objects.create(
        medical_record=record,
        author=doctor_user,
        status=Report.Status.APPROVED,
        content="Approved download body",
    )
    draft_report = Report.objects.create(
        medical_record=record,
        author=doctor_user,
        status=Report.Status.DRAFT,
        content="Draft download body",
    )

    client = Client()
    client.force_login(other_patient)
    unauthorized_patient = client.get(reverse("portal-download-report", args=[approved_report.id]))
    assert unauthorized_patient.status_code == 302

    client.force_login(foreign_doctor)
    unauthorized_doctor = client.get(reverse("portal-download-report", args=[approved_report.id]))
    assert unauthorized_doctor.status_code == 302

    client.force_login(patient_user)
    draft_blocked = client.get(reverse("portal-download-report", args=[draft_report.id]))
    missing_report = client.get(
        reverse("portal-download-report", args=["00000000-0000-0000-0000-000000000000"])
    )

    assert draft_blocked.status_code == 302
    assert missing_report.status_code == 302

    missing_image = client.get(
        reverse("portal-download-image", args=["00000000-0000-0000-0000-000000000000"])
    )
    assert missing_image.status_code == 302

    doctor_only_route = client.post(
        reverse("portal-create-record"), {"patient": "", "diagnosis_text": ""}
    )
    assert doctor_only_route.status_code == 302


@pytest.mark.django_db
def test_portal_doctor_actions_reject_invalid_forms():
    patient_user = User.objects.create_user(
        email="portal-invalid-patient@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    patient_profile = PatientProfile.objects.create(user=patient_user)
    doctor_user = User.objects.create_user(
        email="portal-invalid-doctor@example.com",
        password="StrongPass123",
        role=User.Role.DOCTOR,
    )
    doctor_profile = DoctorProfile.objects.create(user=doctor_user, specialty="Neurology")
    appointment = Appointment.objects.create(
        patient=patient_profile,
        doctor=doctor_profile,
        scheduled_time="2030-01-01T10:00:00Z",
        reason="Invalid branches",
    )

    client = Client()
    client.force_login(doctor_user)

    invalid_status = client.post(
        reverse("portal-update-appointment-status", args=[appointment.id]),
        {"status": "not-a-status"},
        follow=False,
    )
    invalid_diagnosis = client.post(
        reverse("portal-add-diagnosis"),
        {"medical_record": "", "text": ""},
        follow=False,
    )
    invalid_prescription = client.post(
        reverse("portal-add-prescription"),
        {"medical_record": "", "medication_name": "", "dosage": ""},
        follow=False,
    )
    invalid_report = client.post(
        reverse("portal-create-report"),
        {"medical_record": "", "content": ""},
        follow=False,
    )

    assert invalid_status.status_code == 302
    assert invalid_diagnosis.status_code == 302
    assert invalid_prescription.status_code == 302
    assert invalid_report.status_code == 302
