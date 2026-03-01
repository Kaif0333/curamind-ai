from datetime import time, timedelta
from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from .models import User, Appointment


class AppointmentFlowTests(TestCase):
    def setUp(self):
        self.future_date = timezone.localdate() + timedelta(days=7)
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
            date=self.future_date,
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
                "date": str(self.future_date + timedelta(days=1)),
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

    def test_doctor_cannot_book_patient_appointment(self):
        self.client.login(username="doctor1", password="StrongPass123!")
        response = self.client.post(
            reverse("book_appointment"),
            {
                "doctor": self.other_doctor.id,
                "date": str(self.future_date + timedelta(days=2)),
                "time": "12:00",
                "description": "Invalid role action",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_appointment_model_rejects_invalid_roles(self):
        invalid_appointment = Appointment(
            patient=self.doctor,
            doctor=self.patient,
            date=self.future_date + timedelta(days=3),
            time=time(14, 0),
            description="Invalid role mapping",
            status="pending",
        )
        with self.assertRaises(ValidationError):
            invalid_appointment.save()

    def test_cannot_book_past_date(self):
        self.client.login(username="patient1", password="StrongPass123!")
        response = self.client.post(
            reverse("book_appointment"),
            {
                "doctor": self.doctor.id,
                "date": "2020-01-01",
                "time": "09:00",
                "description": "Past booking should fail",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Appointment date cannot be in the past.")

    def test_cannot_double_book_doctor_slot(self):
        self.client.login(username="patient1", password="StrongPass123!")
        response = self.client.post(
            reverse("book_appointment"),
            {
                "doctor": self.doctor.id,
                "date": str(self.future_date),
                "time": "10:30",
                "description": "Conflicting slot request",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already has an appointment for that slot")

    def test_patient_dashboard_status_filter(self):
        self.client.login(username="patient1", password="StrongPass123!")
        response = self.client.get(f"{reverse('patient_dashboard')}?status=pending")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pending")

    def test_doctor_can_reject_legacy_past_appointment(self):
        past_appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.other_doctor,
            date=self.future_date + timedelta(days=1),
            time=time(9, 0),
            description="Legacy past appointment",
            status="pending",
        )
        Appointment.objects.filter(id=past_appointment.id).update(date=timezone.localdate() - timedelta(days=1))

        self.client.login(username="doctor2", password="StrongPass123!")
        response = self.client.post(reverse("reject_appointment", args=[past_appointment.id]))
        self.assertEqual(response.status_code, 302)
        past_appointment.refresh_from_db()
        self.assertEqual(past_appointment.status, "rejected")


class AuthAndRoutingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="patient2",
            password="StrongPass123!",
            user_type="patient",
            email="patient2@example.com",
        )
        self.staff_user = User.objects.create_user(
            username="staff1",
            password="StrongPass123!",
            user_type="patient",
            email="staff1@example.com",
            is_staff=True,
        )

    def test_home_route_available(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CuraMind AI")

    def test_health_route_available(self):
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"status": "ok"})

    def test_docs_route_available(self):
        response = self.client.get(reverse("docs"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_routes_page_available(self):
        response = self.client.get(reverse("routes"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_openapi_schema_available(self):
        response = self.client.get(reverse("api_schema"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_accounts_shortcut_redirects_to_login(self):
        response = self.client.get("/accounts/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_users_root_redirects_to_login_when_anonymous(self):
        response = self.client.get("/users/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_login_shortcut_redirects_to_accounts_login(self):
        response = self.client.get("/login/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_doctor_shortcut_redirects_to_doctor_dashboard_route(self):
        response = self.client.get("/doctor/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/users/doctor/", response.url)

    def test_appointments_shortcut_redirects_to_role_redirect(self):
        response = self.client.get("/appointments/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/users/redirect/", response.url)

    def test_logout_get_not_allowed(self):
        self.client.login(username="patient2", password="StrongPass123!")
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 405)

    def test_logout_post_redirects(self):
        self.client.login(username="patient2", password="StrongPass123!")
        response = self.client.post(reverse("logout"))
        self.assertEqual(response.status_code, 302)

    def test_staff_role_redirect_goes_to_admin(self):
        self.client.login(username="staff1", password="StrongPass123!")
        response = self.client.get(reverse("role_redirect"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/users/patient/")

    def test_staff_can_access_docs_and_routes(self):
        self.client.login(username="staff1", password="StrongPass123!")
        docs_response = self.client.get(reverse("docs"))
        routes_response = self.client.get(reverse("routes"))
        schema_response = self.client.get(reverse("api_schema"))
        self.assertEqual(docs_response.status_code, 200)
        self.assertEqual(routes_response.status_code, 200)
        self.assertEqual(schema_response.status_code, 200)

    def test_superuser_defaults_to_patient_user_type(self):
        superuser = User.objects.create_superuser(
            username="root1",
            email="root1@example.com",
            password="StrongPass123!",
        )
        self.assertEqual(superuser.user_type, "patient")

    def test_superuser_role_redirect_goes_to_admin(self):
        User.objects.create_superuser(
            username="root2",
            email="root2@example.com",
            password="StrongPass123!",
        )
        self.client.login(username="root2", password="StrongPass123!")
        response = self.client.get(reverse("role_redirect"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/admin/")

    def test_registration_page_available(self):
        response = self.client.get(reverse("register"))
        self.assertEqual(response.status_code, 200)

    def test_patient_registration_flow(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "new_patient",
                "email": "new_patient@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="new_patient")
        self.assertEqual(user.user_type, "patient")


class AppointmentAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.future_date = timezone.localdate() + timedelta(days=10)
        self.patient = User.objects.create_user(
            username="api_patient",
            password="StrongPass123!",
            user_type="patient",
            email="api_patient@example.com",
        )
        self.doctor = User.objects.create_user(
            username="api_doctor",
            password="StrongPass123!",
            user_type="doctor",
            email="api_doctor@example.com",
        )
        self.other_patient = User.objects.create_user(
            username="api_other_patient",
            password="StrongPass123!",
            user_type="patient",
            email="api_other_patient@example.com",
        )
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=self.future_date,
            time=time(16, 0),
            description="API appointment",
            status="pending",
        )

    def test_patient_can_list_own_appointments_via_api(self):
        self.client.force_authenticate(user=self.patient)
        response = self.client.get(reverse("api_appointments"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 1)

    def test_patient_can_filter_appointments_by_status(self):
        self.client.force_authenticate(user=self.patient)
        self.appointment.status = "approved"
        self.appointment.save()
        response = self.client.get(f"{reverse('api_appointments')}?status=approved")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)

    def test_patient_filter_invalid_date_returns_400(self):
        self.client.force_authenticate(user=self.patient)
        response = self.client.get(f"{reverse('api_appointments')}?date_from=bad-date")
        self.assertEqual(response.status_code, 400)

    def test_patient_can_create_appointment_via_api(self):
        self.client.force_authenticate(user=self.other_patient)
        response = self.client.post(
            reverse("api_appointments"),
            {
                "doctor": self.doctor.id,
                "date": str(self.future_date + timedelta(days=1)),
                "time": "13:30",
                "description": "Created with API",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "pending")

    def test_doctor_cannot_create_appointment_via_api(self):
        self.client.force_authenticate(user=self.doctor)
        response = self.client.post(
            reverse("api_appointments"),
            {
                "doctor": self.doctor.id,
                "date": str(self.future_date + timedelta(days=1)),
                "time": "13:30",
                "description": "Should fail",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_doctor_can_update_status_via_api(self):
        self.client.force_authenticate(user=self.doctor)
        response = self.client.post(
            reverse("api_appointment_status", args=[self.appointment.id]),
            {"status": "approved"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, "approved")

    def test_patient_cannot_update_status_via_api(self):
        self.client.force_authenticate(user=self.patient)
        response = self.client.post(
            reverse("api_appointment_status", args=[self.appointment.id]),
            {"status": "rejected"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_doctor_dashboard_status_filter(self):
        client = APIClient()
        client.force_authenticate(user=self.doctor)
        response = client.get(f"{reverse('api_appointments')}?status=pending")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data["results"]), 1)


class DataIntegrityAndCommandTests(TestCase):
    def setUp(self):
        self.future_date = timezone.localdate() + timedelta(days=14)
        self.patient = User.objects.create_user(
            username="db_patient",
            password="StrongPass123!",
            user_type="patient",
            email="db_patient@example.com",
        )
        self.doctor = User.objects.create_user(
            username="db_doctor",
            password="StrongPass123!",
            user_type="doctor",
            email="db_doctor@example.com",
        )

    def test_db_unique_constraint_blocks_duplicate_active_slots(self):
        Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=self.future_date,
            time=time(15, 0),
            description="First",
            status="pending",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Appointment.objects.bulk_create(
                    [
                        Appointment(
                            patient=self.patient,
                            doctor=self.doctor,
                            date=self.future_date,
                            time=time(15, 0),
                            description="Duplicate",
                            status="approved",
                        )
                    ]
                )

    def test_seed_demo_command_creates_demo_users(self):
        call_command("seed_demo")
        self.assertTrue(User.objects.filter(username="demo_doctor", user_type="doctor").exists())
        self.assertTrue(User.objects.filter(username="demo_patient", user_type="patient").exists())
