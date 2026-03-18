import base64

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.authentication.models import User
from apps.patients.models import PatientProfile


@pytest.mark.django_db
def test_image_upload():
    user = User.objects.create_user(
        email="patient3@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    PatientProfile.objects.create(user=user)

    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lE"
        "QVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
    )
    upload = SimpleUploadedFile("test.png", png_bytes, content_type="image/png")

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post("/upload-image", {"file": upload}, format="multipart")
    assert response.status_code == 201
    assert "id" in response.data
