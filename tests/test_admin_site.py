from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from apps.authentication.models import User


@pytest.mark.django_db
def test_admin_login_page_uses_curamind_branding():
    follow_response = Client().get(reverse("admin:index"), follow=True)

    assert follow_response.status_code == 200
    assert b"CuraMind AI Control Center" in follow_response.content
    assert b"CuraMind AI Admin" in follow_response.content


@pytest.mark.django_db
def test_admin_index_lists_core_models_after_login():
    admin_user = User.objects.create_superuser(
        email="admin-site@example.com",
        password="StrongPass123",
    )
    client = Client()
    client.force_login(admin_user)

    response = client.get(reverse("admin:index"))

    assert response.status_code == 200
    for label in (
        b"Patient profiles",
        b"Doctor profiles",
        b"Appointments",
        b"Medical records",
        b"Medical images",
        b"Reports",
        b"Clinical operations and platform management",
    ):
        assert label in response.content
