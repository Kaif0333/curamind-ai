from __future__ import annotations

import os
import sys
from typing import cast
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
DJANGO_DIR = ROOT_DIR / "backend" / "django_core"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(DJANGO_DIR) not in sys.path:
    sys.path.insert(0, str(DJANGO_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "curamind_core.settings")

import django  # noqa: E402


def ensure_user(
    *,
    user_model,
    email: str,
    password: str,
    role: str,
    first_name: str,
    last_name: str,
    is_staff: bool = False,
    is_superuser: bool = False,
):
    user, created = user_model.objects.get_or_create(
        email=email,
        defaults={
            "role": role,
            "first_name": first_name,
            "last_name": last_name,
            "is_staff": is_staff,
            "is_superuser": is_superuser,
        },
    )
    updates = []
    if user.role != role:
        user.role = role
        updates.append("role")
    if user.first_name != first_name:
        user.first_name = first_name
        updates.append("first_name")
    if user.last_name != last_name:
        user.last_name = last_name
        updates.append("last_name")
    if user.is_staff != is_staff:
        user.is_staff = is_staff
        updates.append("is_staff")
    if user.is_superuser != is_superuser:
        user.is_superuser = is_superuser
        updates.append("is_superuser")
    user.set_password(password)
    updates.append("password")
    user.save(update_fields=updates)
    state = "created" if created else "updated"
    print(f"{state}: {email}")
    return user


def main() -> None:
    django.setup()

    from apps.appointments.models import Appointment
    from apps.authentication.models import User
    from apps.doctors.models import DoctorProfile
    from apps.medical_records.models import MedicalRecord
    from apps.patients.models import PatientProfile
    from apps.reports.models import Report

    ensure_user(
        user_model=User,
        email="admin@curamind.ai",
        password="AdminPass123!",
        role=cast(str, User.Role.ADMIN),
        first_name="CuraMind",
        last_name="Admin",
        is_staff=True,
        is_superuser=True,
    )
    patient = ensure_user(
        user_model=User,
        email="patient.demo@curamind.ai",
        password="PatientPass123!",
        role=cast(str, User.Role.PATIENT),
        first_name="Amina",
        last_name="Khan",
    )
    doctor = ensure_user(
        user_model=User,
        email="doctor.demo@curamind.ai",
        password="DoctorPass123!",
        role=cast(str, User.Role.DOCTOR),
        first_name="Ravi",
        last_name="Shah",
    )
    radiologist = ensure_user(
        user_model=User,
        email="radiologist.demo@curamind.ai",
        password="RadiologistPass123!",
        role=cast(str, User.Role.RADIOLOGIST),
        first_name="Leena",
        last_name="Roy",
    )

    patient_profile, _ = PatientProfile.objects.get_or_create(
        user=patient,
        defaults={
            "phone": "+1-555-0101",
            "address": "101 Diagnostic Avenue",
            "emergency_contact": "Family Contact",
        },
    )
    doctor_profile, _ = DoctorProfile.objects.get_or_create(
        user=doctor,
        defaults={
            "specialty": "Internal Medicine",
            "license_number": "DOC-1001",
            "phone": "+1-555-0202",
            "department": "Telehealth",
        },
    )
    DoctorProfile.objects.get_or_create(
        user=radiologist,
        defaults={
            "specialty": "Radiology",
            "license_number": "RAD-2001",
            "phone": "+1-555-0303",
            "department": "Imaging",
        },
    )

    appointment, _ = Appointment.objects.get_or_create(
        patient=patient_profile,
        doctor=doctor_profile,
        scheduled_time="2030-01-01T10:00:00Z",
        defaults={
            "reason": "Demo consultation for imaging review",
            "status": Appointment.Status.APPROVED,
        },
    )
    record, _ = MedicalRecord.objects.get_or_create(
        patient=patient_profile,
        doctor=doctor_profile,
        diagnosis_text="Preliminary respiratory assessment for demo workflow.",
        defaults={
            "ai_analysis": {"summary": "No confirmed diagnosis. Awaiting radiology confirmation."}
        },
    )
    Report.objects.get_or_create(
        medical_record=record,
        author=doctor,
        content="Draft report created for the seeded demo patient workflow.",
        defaults={"status": Report.Status.DRAFT},
    )

    print("seeded appointment:", appointment.id)
    print("seeded medical record:", record.id)
    print("admin login: admin@curamind.ai / AdminPass123!")
    print("patient login: patient.demo@curamind.ai / PatientPass123!")
    print("doctor login: doctor.demo@curamind.ai / DoctorPass123!")
    print("radiologist login: radiologist.demo@curamind.ai / RadiologistPass123!")


if __name__ == "__main__":
    main()
