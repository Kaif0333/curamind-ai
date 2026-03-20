import pytest
from rest_framework.test import APIClient

from apps.appointments.models import Appointment
from apps.authentication.models import User
from apps.doctors.models import DoctorProfile
from apps.patients.models import PatientProfile


@pytest.mark.django_db
def test_patient_can_create_appointment():
    patient_user = User.objects.create_user(
        email="patient2@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    PatientProfile.objects.create(user=patient_user)

    doctor_user = User.objects.create_user(
        email="doctor@example.com",
        password="StrongPass123",
        role=User.Role.DOCTOR,
    )
    doctor_profile = DoctorProfile.objects.create(user=doctor_user, specialty="Cardiology")

    client = APIClient()
    client.force_authenticate(user=patient_user)
    payload = {
        "doctor_id": str(doctor_profile.id),
        "scheduled_time": "2030-01-01T10:00:00Z",
        "reason": "Checkup",
    }
    response = client.post("/appointments", payload, format="json")
    assert response.status_code == 201
    assert Appointment.objects.count() == 1


@pytest.mark.django_db
def test_patient_cannot_book_radiologist_as_appointment_doctor():
    patient_user = User.objects.create_user(
        email="patient4@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    PatientProfile.objects.create(user=patient_user)

    radiologist_user = User.objects.create_user(
        email="radiologist@example.com",
        password="StrongPass123",
        role=User.Role.RADIOLOGIST,
    )
    radiologist_profile = DoctorProfile.objects.create(user=radiologist_user, specialty="Radiology")

    client = APIClient()
    client.force_authenticate(user=patient_user)
    response = client.post(
        "/appointments",
        {
            "doctor_id": str(radiologist_profile.id),
            "scheduled_time": "2030-01-01T10:00:00Z",
            "reason": "Should fail",
        },
        format="json",
    )

    assert response.status_code == 404
    assert Appointment.objects.count() == 0


@pytest.mark.django_db
def test_patient_cannot_create_past_appointment():
    patient_user = User.objects.create_user(
        email="patient5@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    PatientProfile.objects.create(user=patient_user)

    doctor_user = User.objects.create_user(
        email="doctor2@example.com",
        password="StrongPass123",
        role=User.Role.DOCTOR,
    )
    doctor_profile = DoctorProfile.objects.create(user=doctor_user, specialty="Cardiology")

    client = APIClient()
    client.force_authenticate(user=patient_user)
    response = client.post(
        "/appointments",
        {
            "doctor_id": str(doctor_profile.id),
            "scheduled_time": "2020-01-01T10:00:00Z",
            "reason": "Past appointment",
        },
        format="json",
    )

    assert response.status_code == 400
    assert "scheduled_time" in response.data


@pytest.mark.django_db
def test_patient_can_list_and_cancel_own_appointment():
    patient_user = User.objects.create_user(
        email="patient6@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    patient_profile = PatientProfile.objects.create(user=patient_user)

    doctor_user = User.objects.create_user(
        email="doctor3@example.com",
        password="StrongPass123",
        role=User.Role.DOCTOR,
    )
    doctor_profile = DoctorProfile.objects.create(user=doctor_user, specialty="Cardiology")
    appointment = Appointment.objects.create(
        patient=patient_profile,
        doctor=doctor_profile,
        scheduled_time="2030-01-01T10:00:00Z",
        reason="Follow-up",
    )

    client = APIClient()
    client.force_authenticate(user=patient_user)

    list_response = client.get("/appointments")
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.data] == [str(appointment.id)]

    cancel_response = client.patch(f"/appointments/{appointment.id}/cancel", {}, format="json")
    assert cancel_response.status_code == 200

    appointment.refresh_from_db()
    assert appointment.status == Appointment.Status.CANCELLED
