from datetime import date, time
from django.test import TestCase
from django.urls import reverse
from .models import User, Appointment


class AppointmentFlowTests(TestCase):
    def setUp(self):
        self.patient = User.objects.create_user(
            username="patient1",
            password="StrongPass123!",
            user_type="patient",
            email="patient1@example.com",
        )
        self.doctor = User.objects.create_user(
            username="doctor1",
            password="StrongPass123!",
            user_type="doctor",
            email="doctor1@example.com",
        )
        self.other_doctor = User.objects.create_user(
            username="doctor2",
            password="StrongPass123!",
            user_type="doctor",
            email="doctor2@example.com",
        )
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=date(2026, 2, 24),
            time=time(10, 30),
            description="Routine consultation",
            status="pending",
        )

    def test_patient_cannot_access_doctor_dashboard(self):
        self.client.login(username="patient1", password="StrongPass123!")
        response = self.client.get(reverse("doctor_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_doctor_cannot_access_patient_dashboard(self):
        self.client.login(username="doctor1", password="StrongPass123!")
        response = self.client.get(reverse("patient_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_patient_can_book_appointment_with_valid_doctor(self):
        self.client.login(username="patient1", password="StrongPass123!")
        response = self.client.post(
            reverse("book_appointment"),
            {
                "doctor": self.other_doctor.id,
                "date": "2026-03-01",
                "time": "11:00",
                "description": "Follow-up",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Appointment.objects.filter(
                patient=self.patient,
                doctor=self.other_doctor,
                status="pending",
                description="Follow-up",
            ).exists()
        )

    def test_doctor_can_approve_own_appointment(self):
        self.client.login(username="doctor1", password="StrongPass123!")
        response = self.client.post(reverse("approve_appointment", args=[self.appointment.id]))
        self.assertEqual(response.status_code, 302)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, "approved")

    def test_doctor_cannot_approve_other_doctor_appointment(self):
        self.client.login(username="doctor2", password="StrongPass123!")
        response = self.client.post(reverse("approve_appointment", args=[self.appointment.id]))
        self.assertEqual(response.status_code, 404)

    def test_approve_appointment_get_not_allowed(self):
        self.client.login(username="doctor1", password="StrongPass123!")
        response = self.client.get(reverse("approve_appointment", args=[self.appointment.id]))
        self.assertEqual(response.status_code, 405)
