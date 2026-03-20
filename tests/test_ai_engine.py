import pytest
from rest_framework.test import APIClient

from apps.authentication.models import User
from apps.imaging.models import MedicalImage
from apps.patients.models import PatientProfile


@pytest.mark.django_db
def test_patient_can_view_processing_logs_for_own_image(monkeypatch):
    user = User.objects.create_user(
        email="ai-patient@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    patient_profile = PatientProfile.objects.create(user=user)
    image = MedicalImage.objects.create(
        patient=patient_profile,
        uploaded_by=user,
        file_name="scan.png",
        s3_key="medical-images/scan.png",
        modality="MRI",
        content_type="image/png",
        file_size=123,
        metadata={},
    )

    monkeypatch.setattr(
        "apps.ai_engine.views.get_processing_logs_by_image",
        lambda image_id: [{"image_id": image_id, "stage": "upload", "status": "completed"}],
    )

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(f"/ai/logs?image_id={image.id}")

    assert response.status_code == 200
    assert response.data[0]["stage"] == "upload"
