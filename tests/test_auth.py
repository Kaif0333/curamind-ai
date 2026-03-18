import pytest
from rest_framework.test import APIClient

from apps.authentication.models import User


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
