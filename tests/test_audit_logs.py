import pytest
from django.test import Client
from django.urls import reverse
from rest_framework.test import APIClient

from apps.audit_logs.models import AuditLog
from apps.authentication.models import User


@pytest.mark.django_db
def test_admin_can_list_and_filter_audit_logs_via_api():
    admin_user = User.objects.create_user(
        email="admin-audit@example.com",
        password="StrongPass123",
        role=User.Role.ADMIN,
        is_staff=True,
    )
    other_user = User.objects.create_user(
        email="doctor-audit@example.com",
        password="StrongPass123",
        role=User.Role.DOCTOR,
    )
    AuditLog.objects.create(user=other_user, action="login", resource_id="user-1")
    AuditLog.objects.create(user=other_user, action="report_download", resource_id="report-1")

    client = APIClient()
    client.force_authenticate(user=admin_user)
    response = client.get("/audit-logs", {"action": "login"})

    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["action"] == "login"


@pytest.mark.django_db
def test_admin_dashboard_can_filter_audit_logs():
    admin_user = User.objects.create_user(
        email="admin-dashboard@example.com",
        password="StrongPass123",
        role=User.Role.ADMIN,
        is_staff=True,
    )
    patient_user = User.objects.create_user(
        email="patient-audit@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    AuditLog.objects.create(user=patient_user, action="login", resource_id="resource-1")
    AuditLog.objects.create(user=patient_user, action="record_view", resource_id="resource-2")

    client = Client()
    client.force_login(admin_user)
    response = client.get(reverse("portal-dashboard"), {"action": "login"})

    assert response.status_code == 200
    assert b"login" in response.content
    assert b"record_view" not in response.content
