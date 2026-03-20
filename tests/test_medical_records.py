import pytest
from rest_framework.test import APIClient

from apps.appointments.models import Appointment
from apps.authentication.models import User
from apps.doctors.models import DoctorProfile
from apps.medical_records.models import Diagnosis, MedicalRecord, Prescription
from apps.patients.models import PatientProfile


@pytest.mark.django_db
def test_doctor_can_add_diagnosis_and_prescription_to_own_record():
    patient_user = User.objects.create_user(
        email="records-patient@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    patient_profile = PatientProfile.objects.create(user=patient_user)

    doctor_user = User.objects.create_user(
        email="records-doctor@example.com",
        password="StrongPass123",
        role=User.Role.DOCTOR,
    )
    doctor_profile = DoctorProfile.objects.create(user=doctor_user, specialty="Neurology")
    Appointment.objects.create(
        patient=patient_profile,
        doctor=doctor_profile,
        scheduled_time="2030-01-01T10:00:00Z",
        reason="Neurology consult",
    )
    record = MedicalRecord.objects.create(
        patient=patient_profile,
        doctor=doctor_profile,
        diagnosis_text="Initial diagnosis",
    )

    client = APIClient()
    client.force_authenticate(user=doctor_user)

    diagnosis_response = client.post(
        f"/records/{record.id}/diagnoses",
        {"text": "Confirmed migraine with aura"},
        format="json",
    )
    prescription_response = client.post(
        f"/records/{record.id}/prescriptions",
        {
            "medication_name": "Sumatriptan",
            "dosage": "50mg",
            "instructions": "Take at onset of symptoms.",
        },
        format="json",
    )

    assert diagnosis_response.status_code == 201
    assert prescription_response.status_code == 201
    assert Diagnosis.objects.filter(medical_record=record, text__icontains="migraine").exists()
    assert Prescription.objects.filter(
        medical_record=record, medication_name="Sumatriptan"
    ).exists()


@pytest.mark.django_db
def test_patient_can_view_diagnoses_and_prescriptions_for_own_record():
    patient_user = User.objects.create_user(
        email="records-patient2@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    patient_profile = PatientProfile.objects.create(user=patient_user)

    doctor_user = User.objects.create_user(
        email="records-doctor2@example.com",
        password="StrongPass123",
        role=User.Role.DOCTOR,
    )
    doctor_profile = DoctorProfile.objects.create(user=doctor_user, specialty="Cardiology")
    record = MedicalRecord.objects.create(
        patient=patient_profile,
        doctor=doctor_profile,
        diagnosis_text="Cardiology review",
    )
    Diagnosis.objects.create(medical_record=record, text="Hypertension")
    Prescription.objects.create(
        medical_record=record,
        medication_name="Lisinopril",
        dosage="10mg",
        instructions="Daily",
    )

    client = APIClient()
    client.force_authenticate(user=patient_user)

    diagnoses_response = client.get(f"/records/{record.id}/diagnoses")
    prescriptions_response = client.get(f"/records/{record.id}/prescriptions")

    assert diagnoses_response.status_code == 200
    assert prescriptions_response.status_code == 200
    assert diagnoses_response.data[0]["text"] == "Hypertension"
    assert prescriptions_response.data[0]["medication_name"] == "Lisinopril"


@pytest.mark.django_db
@pytest.mark.parametrize("role", [User.Role.RADIOLOGIST, User.Role.ADMIN])
def test_non_care_team_roles_cannot_view_record_details(role):
    patient_user = User.objects.create_user(
        email=f"records-private-{role}@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    patient_profile = PatientProfile.objects.create(user=patient_user)

    doctor_user = User.objects.create_user(
        email=f"records-owner-{role}@example.com",
        password="StrongPass123",
        role=User.Role.DOCTOR,
    )
    doctor_profile = DoctorProfile.objects.create(user=doctor_user, specialty="General")
    record = MedicalRecord.objects.create(
        patient=patient_profile,
        doctor=doctor_profile,
        diagnosis_text="Sensitive case",
    )
    Diagnosis.objects.create(medical_record=record, text="Restricted diagnosis")
    Prescription.objects.create(
        medical_record=record,
        medication_name="Restricted prescription",
        dosage="5mg",
        instructions="Private",
    )

    outsider_user = User.objects.create_user(
        email=f"outsider-{role}@example.com",
        password="StrongPass123",
        role=role,
        is_staff=role == User.Role.ADMIN,
    )
    if role == User.Role.RADIOLOGIST:
        DoctorProfile.objects.create(user=outsider_user, specialty="Radiology")

    client = APIClient()
    client.force_authenticate(user=outsider_user)

    diagnoses_response = client.get(f"/records/{record.id}/diagnoses")
    prescriptions_response = client.get(f"/records/{record.id}/prescriptions")

    assert diagnoses_response.status_code == 404
    assert prescriptions_response.status_code == 404
