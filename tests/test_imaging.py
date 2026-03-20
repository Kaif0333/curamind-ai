import base64
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.authentication.models import User
from apps.imaging.models import MedicalImage
from apps.imaging.storage import S3StorageService
from apps.imaging.tasks import ai_inference_task
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


@pytest.mark.django_db
def test_ai_inference_task_marks_image_processed(monkeypatch):
    user = User.objects.create_user(
        email="patient4@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    patient_profile = PatientProfile.objects.create(user=user)

    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElE"
        "QVR42mP8/5+hHgAHggJ/Pk9xWQAAAABJRU5ErkJggg=="
    )
    storage = S3StorageService()
    key = storage.build_key("task-test.png")
    storage.upload(BytesIO(png_bytes), key)

    image = MedicalImage.objects.create(
        patient=patient_profile,
        uploaded_by=user,
        file_name="task-test.png",
        s3_key=key,
        modality="X-Ray",
        content_type="image/png",
        file_size=len(png_bytes),
        metadata={},
    )

    monkeypatch.setattr(
        "apps.imaging.tasks.request_inference",
        lambda image_bytes, image_id: {"anomaly_probability": 0.1},
    )

    ai_inference_task(str(image.id))
    image.refresh_from_db()

    assert image.status == MedicalImage.Status.PROCESSED


@pytest.mark.django_db
def test_ai_inference_task_records_processing_log_events(monkeypatch):
    user = User.objects.create_user(
        email="patient6@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    patient_profile = PatientProfile.objects.create(user=user)

    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElE"
        "QVR42mP8/5+hHgAHggJ/Pk9xWQAAAABJRU5ErkJggg=="
    )
    storage = S3StorageService()
    key = storage.build_key("task-log-test.png")
    storage.upload(BytesIO(png_bytes), key)

    image = MedicalImage.objects.create(
        patient=patient_profile,
        uploaded_by=user,
        file_name="task-log-test.png",
        s3_key=key,
        modality="X-Ray",
        content_type="image/png",
        file_size=len(png_bytes),
        metadata={},
    )
    logged_events = []

    monkeypatch.setattr(
        "apps.imaging.tasks.request_inference",
        lambda image_bytes, image_id: {"anomaly_probability": 0.25},
    )
    monkeypatch.setattr(
        "apps.imaging.tasks.store_processing_log",
        lambda image_id, stage, status, details=None: logged_events.append(
            {
                "image_id": image_id,
                "stage": stage,
                "status": status,
                "details": details or {},
            }
        ),
    )

    ai_inference_task(str(image.id))

    assert [event["status"] for event in logged_events] == ["started", "completed"]
    assert logged_events[0]["stage"] == "inference"
    assert logged_events[1]["details"]["anomaly_probability"] == 0.25


@pytest.mark.django_db
def test_ai_inference_task_marks_image_failed_when_file_missing():
    user = User.objects.create_user(
        email="patient5@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    patient_profile = PatientProfile.objects.create(user=user)
    image = MedicalImage.objects.create(
        patient=patient_profile,
        uploaded_by=user,
        file_name="missing.png",
        s3_key="medical-images/missing.png",
        modality="X-Ray",
        content_type="image/png",
        file_size=123,
        metadata={},
    )

    ai_inference_task(str(image.id))
    image.refresh_from_db()

    assert image.status == MedicalImage.Status.FAILED
    assert "processing_error" in image.metadata
