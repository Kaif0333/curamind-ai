import pyotp
import pytest
from django.test import Client
from django.urls import reverse
from rest_framework.test import APIClient

from apps.authentication.mfa import generate_mfa_secret
from apps.authentication.models import User
from apps.patients.models import PatientProfile


@pytest.mark.django_db
def test_authenticated_user_can_enable_and_disable_mfa_via_api():
    user = User.objects.create_user(
        email="mfa-user@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    PatientProfile.objects.create(user=user)

    client = APIClient()
    client.force_authenticate(user=user)

    setup_response = client.post("/auth/mfa/setup", {}, format="json")
    assert setup_response.status_code == 200
    secret = setup_response.data["secret"]
    code = pyotp.TOTP(secret).now()

    verify_response = client.post("/auth/mfa/verify", {"code": code}, format="json")
    assert verify_response.status_code == 200

    user.refresh_from_db()
    assert user.mfa_enabled is True

    disable_code = pyotp.TOTP(user.mfa_secret).now()
    disable_response = client.post(
        "/auth/mfa/disable",
        {"password": "StrongPass123", "code": disable_code},
        format="json",
    )
    assert disable_response.status_code == 200

    user.refresh_from_db()
    assert user.mfa_enabled is False
    assert user.mfa_secret == ""


@pytest.mark.django_db
def test_login_requires_mfa_and_can_be_completed_with_challenge():
    secret = generate_mfa_secret()
    user = User.objects.create_user(
        email="mfa-login@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
        mfa_enabled=True,
        mfa_secret=secret,
    )
    PatientProfile.objects.create(user=user)

    client = APIClient()
    login_response = client.post(
        "/auth/login",
        {"email": user.email, "password": "StrongPass123"},
        format="json",
    )

    assert login_response.status_code == 202
    assert login_response.data["mfa_required"] is True
    assert "challenge_token" in login_response.data
    assert "access" not in login_response.data

    code = pyotp.TOTP(secret).now()
    verify_response = client.post(
        "/auth/login/mfa-verify",
        {
            "challenge_token": login_response.data["challenge_token"],
            "code": code,
        },
        format="json",
    )

    assert verify_response.status_code == 200
    assert "access" in verify_response.data
    assert "refresh" in verify_response.data


@pytest.mark.django_db
def test_portal_login_requires_mfa_when_enabled():
    secret = generate_mfa_secret()
    user = User.objects.create_user(
        email="portal-mfa@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
        mfa_enabled=True,
        mfa_secret=secret,
    )
    PatientProfile.objects.create(user=user)

    client = Client()
    login_response = client.post(
        reverse("portal-login"),
        {"email": user.email, "password": "StrongPass123"},
        follow=False,
    )

    assert login_response.status_code == 302
    assert login_response.url == reverse("portal-mfa-login")

    verify_response = client.post(
        reverse("portal-mfa-login"),
        {"code": pyotp.TOTP(secret).now()},
        follow=False,
    )

    assert verify_response.status_code == 302
    assert verify_response.url == reverse("portal-dashboard")
