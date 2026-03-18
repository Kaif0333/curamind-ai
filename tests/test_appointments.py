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
