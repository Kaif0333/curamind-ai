import base64
from io import BytesIO

import pydicom
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, SecondaryCaptureImageStorage, generate_uid
from rest_framework.test import APIClient

from apps.authentication.models import User
from apps.imaging.models import MedicalImage
from apps.imaging.storage import S3StorageService
from apps.imaging.tasks import ai_inference_task
from apps.patients.models import PatientProfile


def build_test_dicom_bytes() -> bytes:
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationClassUID = generate_uid()

    dataset = FileDataset("test.dcm", {}, file_meta=file_meta, preamble=b"\0" * 128)
    dataset.PatientName = "Sensitive Name"
    dataset.PatientID = "ABC123"
    dataset.PatientBirthDate = "19900101"
    dataset.Modality = "MRI"
    dataset.Rows = 1
    dataset.Columns = 1
    dataset.SamplesPerPixel = 1
    dataset.PhotometricInterpretation = "MONOCHROME2"
    dataset.PixelRepresentation = 0
    dataset.BitsStored = 8
    dataset.BitsAllocated = 8
    dataset.HighBit = 7
    dataset.PixelData = b"\x00"

    buffer = BytesIO()
    dataset.save_as(buffer, write_like_original=False)
    return buffer.getvalue()


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
    assert "/imaging/" in response.data["download_url"]


@pytest.mark.django_db
def test_dicom_upload_is_deidentified_before_storage():
    user = User.objects.create_user(
        email="patient-dicom@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    PatientProfile.objects.create(user=user)

    upload = SimpleUploadedFile(
        "scan.dcm",
        build_test_dicom_bytes(),
        content_type="application/dicom",
    )

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post("/upload-image", {"file": upload}, format="multipart")

    assert response.status_code == 201
    image = MedicalImage.objects.get(id=response.data["id"])

    storage = S3StorageService()
    stored_bytes = storage.download(image.s3_key)
    dataset = pydicom.dcmread(BytesIO(stored_bytes))

    assert not hasattr(dataset, "PatientName")
    assert not hasattr(dataset, "PatientID")
    assert dataset.Modality == "MRI"
    assert image.metadata["Modality"] == "MRI"
    assert image.metadata["_deidentified"] == "true"
    assert "PatientName" not in image.metadata


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


@pytest.mark.django_db
def test_patient_can_download_own_image_but_other_patient_cannot():
    owner_user = User.objects.create_user(
        email="patient-owner@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    owner_profile = PatientProfile.objects.create(user=owner_user)
    other_user = User.objects.create_user(
        email="patient-other@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    PatientProfile.objects.create(user=other_user)

    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lE"
        "QVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
    )
    storage = S3StorageService()
    key = storage.build_key("private-test.png")
    storage.upload(BytesIO(png_bytes), key)

    image = MedicalImage.objects.create(
        patient=owner_profile,
        uploaded_by=owner_user,
        file_name="private-test.png",
        s3_key=key,
        modality="X-Ray",
        content_type="image/png",
        file_size=len(png_bytes),
        metadata={},
    )

    owner_client = APIClient()
    owner_client.force_authenticate(user=owner_user)
    owner_response = owner_client.get(f"/imaging/{image.id}/download")

    other_client = APIClient()
    other_client.force_authenticate(user=other_user)
    other_response = other_client.get(f"/imaging/{image.id}/download")

    assert owner_response.status_code == 200
    assert b"".join(owner_response.streaming_content) == png_bytes
    assert other_response.status_code == 404


@pytest.mark.django_db
def test_admin_cannot_download_patient_image():
    owner_user = User.objects.create_user(
        email="patient-owner-admin-test@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    owner_profile = PatientProfile.objects.create(user=owner_user)
    admin_user = User.objects.create_user(
        email="admin-no-image@example.com",
        password="StrongPass123",
        role=User.Role.ADMIN,
        is_staff=True,
    )

    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lE"
        "QVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII="
    )
    storage = S3StorageService()
    key = storage.build_key("admin-private-test.png")
    storage.upload(BytesIO(png_bytes), key)

    image = MedicalImage.objects.create(
        patient=owner_profile,
        uploaded_by=owner_user,
        file_name="admin-private-test.png",
        s3_key=key,
        modality="X-Ray",
        content_type="image/png",
        file_size=len(png_bytes),
        metadata={},
    )

    client = APIClient()
    client.force_authenticate(user=admin_user)
    response = client.get(f"/imaging/{image.id}/download")

    assert response.status_code == 404
