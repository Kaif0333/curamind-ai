import pytest
from rest_framework.test import APIClient

from apps.authentication.models import User
from apps.patients.models import PatientProfile


@pytest.mark.django_db
def test_register_and_login():
    client = APIClient()
    register_payload = {
        "email": "patient@example.com",
        "password": "StrongPass123",
        "first_name": "Pat",
        "last_name": "Smith",
        "role": User.Role.PATIENT,
    }
    response = client.post("/auth/register", register_payload, format="json")
    assert response.status_code == 201

    login_payload = {"email": "patient@example.com", "password": "StrongPass123"}
    response = client.post("/auth/login", login_payload, format="json")
    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh" in response.data


@pytest.mark.django_db
def test_register_cannot_self_assign_admin_role_by_default():
    client = APIClient()
    response = client.post(
        "/auth/register",
        {
            "email": "would-be-admin@example.com",
            "password": "StrongPass123",
            "first_name": "Not",
            "last_name": "Admin",
            "role": User.Role.ADMIN,
        },
        format="json",
    )

    assert response.status_code == 201
    user = User.objects.get(email="would-be-admin@example.com")
    assert user.role == User.Role.PATIENT
    assert user.is_superuser is False
    assert PatientProfile.objects.filter(user=user).exists()
