from datetime import timedelta, time
from django.core.management.base import BaseCommand
from django.utils import timezone
from users.models import User, Appointment


class Command(BaseCommand):
    help = "Create demo users and appointments for local testing."

    def handle(self, *args, **options):
        doctor = User.objects.filter(username="demo_doctor").first()
        if not doctor:
            doctor = User.objects.create_user(
                username="demo_doctor",
                email="doctor@curamind.local",
                password="DemoPass123!",
                user_type="doctor",
            )
        else:
            doctor.email = doctor.email or "doctor@curamind.local"
            doctor.user_type = "doctor"
            doctor.save()

        patient = User.objects.filter(username="demo_patient").first()
        if not patient:
            patient = User.objects.create_user(
                username="demo_patient",
                email="patient@curamind.local",
                password="DemoPass123!",
                user_type="patient",
            )
        else:
            patient.email = patient.email or "patient@curamind.local"
            patient.user_type = "patient"
            patient.save()

        start_date = timezone.localdate() + timedelta(days=1)
        for index in range(3):
            Appointment.objects.get_or_create(
                patient=patient,
                doctor=doctor,
                date=start_date + timedelta(days=index),
                time=time(10 + index, 0),
                defaults={
                    "description": f"Demo appointment {index + 1}",
                    "status": "pending",
                },
            )

        self.stdout.write(self.style.SUCCESS("Demo data ready."))
        self.stdout.write("Doctor login: demo_doctor / DemoPass123!")
        self.stdout.write("Patient login: demo_patient / DemoPass123!")
