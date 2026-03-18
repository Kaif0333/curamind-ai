import base64

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse

from apps.appointments.models import Appointment
from apps.authentication.models import User
from apps.doctors.models import DoctorProfile
from apps.imaging.models import MedicalImage
from apps.patients.models import PatientProfile


@pytest.mark.django_db
def test_portal_home_renders():
    client = Client()
    response = client.get(reverse("portal-home"))
    assert response.status_code == 200
    assert b"CuraMind AI" in response.content


@pytest.mark.django_db
def test_patient_portal_can_book_appointment_and_upload_image():
    patient_user = User.objects.create_user(
        email="portal-patient@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    PatientProfile.objects.create(user=patient_user)

    doctor_user = User.objects.create_user(
        email="portal-doctor@example.com",
        password="StrongPass123",
        role=User.Role.DOCTOR,
    )
    doctor_profile = DoctorProfile.objects.create(user=doctor_user, specialty="Radiology")

    client = Client()
    client.force_login(patient_user)

    appointment_response = client.post(
        reverse("portal-book-appointment"),
        {
            "doctor": str(doctor_profile.id),
            "scheduled_time": "2030-01-01T10:00",
            "reason": "Follow-up scan review",
        },
    )
    assert appointment_response.status_code == 302
    assert Appointment.objects.count() == 1

    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lE"
        "QVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
    )
    upload = SimpleUploadedFile("portal-test.png", png_bytes, content_type="image/png")
    image_response = client.post(
        reverse("portal-upload-image"),
        {"file": upload, "modality": "X-Ray"},
    )
    assert image_response.status_code == 302
    assert MedicalImage.objects.count() == 1

    dashboard_response = client.get(reverse("portal-dashboard"))
    assert dashboard_response.status_code == 200
    assert b"Your care timeline at a glance." in dashboard_response.content
