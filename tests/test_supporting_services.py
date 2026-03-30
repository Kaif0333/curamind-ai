from __future__ import annotations

from io import BytesIO

import pytest
from botocore.exceptions import ClientError
from requests import RequestException
from rest_framework.test import APIClient

from apps.ai_engine import mongo as ai_mongo
from apps.ai_engine.service import (
    AIServiceRequestError,
    AIServiceResponseError,
    request_inference,
)
from apps.appointments.models import Appointment
from apps.authentication.models import LoginAttempt, User
from apps.doctors.models import DoctorProfile
from apps.imaging.storage import S3StorageService, StorageError
from apps.medical_records.models import MedicalRecord
from apps.notifications.tasks import send_email_notification
from apps.patients.models import PatientProfile
from apps.reports.models import Report


class _FakeResponse:
    def __init__(self, payload: dict, headers: dict | None = None):
        self._payload = payload
        self.headers = headers or {}

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _InvalidJSONResponse(_FakeResponse):
    def json(self):
        raise ValueError("bad json")


class _StatusErrorResponse(_FakeResponse):
    def __init__(self, status_code: int):
        super().__init__({})
        self.status_code = status_code

    def raise_for_status(self):
        response = type("Response", (), {"status_code": self.status_code})()
        raise RequestException("request failed", response=response)


@pytest.mark.django_db
def test_user_manager_and_model_strings():
    with pytest.raises(ValueError):
        User.objects.create_user(email="", password="StrongPass123")

    admin = User.objects.create_superuser(
        email="super@example.com",
        password="StrongPass123",
    )
    attempt = LoginAttempt.objects.create(
        user=admin,
        email=admin.email,
        success=True,
    )

    assert admin.is_staff is True
    assert admin.is_superuser is True
    assert admin.role == User.Role.ADMIN
    assert str(admin) == "super@example.com (admin)"
    assert str(attempt) == "super@example.com - success"


def test_request_inference_stores_payload(monkeypatch):
    stored = {}
    observed = {}

    monkeypatch.setattr(
        "apps.ai_engine.service.requests.post",
        lambda *args, **kwargs: (
            observed.update({"headers": kwargs.get("headers")})
            or _FakeResponse(
                {"anomaly_probability": 0.31, "heatmap": "abc", "model": "resnet50"},
                headers={"X-Process-Time-Ms": "15.4", "X-Image-SHA256": "server-sha"},
            )
        ),
    )
    monkeypatch.setattr(
        "apps.ai_engine.service.store_ai_result",
        lambda image_id, payload: stored.update({"image_id": image_id, "payload": payload}),
    )

    payload = request_inference(b"img-bytes", "image-123")

    assert payload["anomaly_probability"] == 0.31
    assert stored["image_id"] == "image-123"
    assert stored["payload"]["model"] == "resnet50"
    assert stored["payload"]["service_processing_ms"] == 15.4
    assert stored["payload"]["input_sha256"] == "server-sha"
    assert stored["payload"]["image_id"] == "image-123"
    assert observed["headers"]["X-Image-Id"] == "image-123"
    assert observed["headers"]["X-Image-SHA256"]


def test_request_inference_rejects_transport_and_payload_failures(monkeypatch):
    monkeypatch.setattr(
        "apps.ai_engine.service.requests.post",
        lambda *args, **kwargs: (_ for _ in ()).throw(RequestException("network down")),
    )

    with pytest.raises(AIServiceRequestError):
        request_inference(b"img-bytes", "image-transport")

    monkeypatch.setattr(
        "apps.ai_engine.service.requests.post",
        lambda *args, **kwargs: _InvalidJSONResponse({}),
    )
    with pytest.raises(AIServiceResponseError):
        request_inference(b"img-bytes", "image-json")

    monkeypatch.setattr(
        "apps.ai_engine.service.requests.post",
        lambda *args, **kwargs: _FakeResponse({"heatmap": "abc", "model": "resnet50"}),
    )
    with pytest.raises(AIServiceResponseError):
        request_inference(b"img-bytes", "image-payload")


def test_request_inference_retries_transient_service_failures(monkeypatch):
    calls = {"count": 0}

    def fake_post(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] < 3:
            return _StatusErrorResponse(503)
        return _FakeResponse(
            {
                "anomaly_probability": 0.44,
                "heatmap": "abc",
                "model": "resnet50",
                "model_version": "demo-resnet50-v1",
                "device": "cpu",
            }
        )

    monkeypatch.setattr("apps.ai_engine.service.requests.post", fake_post)
    monkeypatch.setattr("apps.ai_engine.service.time.sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("apps.ai_engine.service.AI_SERVICE_RETRY_COUNT", 2)
    monkeypatch.setattr(
        "apps.ai_engine.service.store_ai_result",
        lambda *_args, **_kwargs: None,
    )

    payload = request_inference(b"img-bytes", "image-retry")

    assert payload["anomaly_probability"] == 0.44
    assert calls["count"] == 3


def test_send_email_notification_handles_empty_recipient_and_failures(monkeypatch):
    send_email_notification("", "Subject", "Body")

    monkeypatch.setattr(
        "apps.notifications.tasks.send_mail",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("mail down")),
    )

    send_email_notification("patient@example.com", "Subject", "Body")


def test_local_storage_service_round_trip(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.AWS_ACCESS_KEY_ID = ""
    settings.AWS_SECRET_ACCESS_KEY = ""
    settings.AWS_S3_PRIVATE_BUCKET = ""

    storage = S3StorageService()
    key = storage.build_key("demo image.png")
    stored_key = storage.upload(BytesIO(b"payload"), key)

    assert stored_key == key
    assert storage.download(key) == b"payload"
    assert storage.presigned_url(key).endswith(key.replace("/", "_"))
    assert storage.open_file(key).read() == b"payload"

    direct_file = tmp_path / "standalone.bin"
    direct_file.write_bytes(b"direct")
    assert storage.download(str(direct_file)) == b"direct"


def test_s3_storage_service_raises_storage_error(settings, monkeypatch, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.AWS_ACCESS_KEY_ID = "key"
    settings.AWS_SECRET_ACCESS_KEY = "secret"
    settings.AWS_S3_PRIVATE_BUCKET = "bucket"
    settings.AWS_REGION = "us-east-1"

    class FakeClient:
        def upload_fileobj(self, *args, **kwargs):
            raise ClientError({"Error": {"Code": "500", "Message": "boom"}}, "Upload")

        def get_object(self, *args, **kwargs):
            raise ClientError({"Error": {"Code": "404", "Message": "missing"}}, "GetObject")

        def generate_presigned_url(self, *args, **kwargs):
            return "https://example.com/presigned"

    monkeypatch.setattr("apps.imaging.storage.boto3.client", lambda *args, **kwargs: FakeClient())

    storage = S3StorageService()

    with pytest.raises(StorageError):
        storage.upload(BytesIO(b"payload"), "medical-images/fail.bin")

    with pytest.raises(StorageError):
        storage.download("medical-images/missing.bin")

    assert storage.presigned_url("medical-images/ok.bin") == "https://example.com/presigned"


def test_ai_mongo_helpers(monkeypatch):
    inserted_docs = {"ai_results": [], "image_metadata": [], "processing_logs": []}
    created_indexes = []

    class FakeCollection:
        def __init__(self, name):
            self.name = name

        def create_index(self, keys, **kwargs):
            created_indexes.append((self.name, keys, kwargs))
            return f"{self.name}-index"

        def replace_one(self, query, doc, upsert=False):
            assert upsert is True
            inserted_docs[self.name].append({"query": query, "doc": doc})
            return type("WriteResult", (), {"upserted_id": f"{self.name}-id"})()

        def insert_one(self, doc):
            inserted_docs[self.name].append(doc)
            return type("Inserted", (), {"inserted_id": f"{self.name}-id"})()

        def find_one(self, query, sort=None):
            if self.name == "ai_results" and query == {"image_id": "img-1"}:
                latest = inserted_docs[self.name][-1]["doc"] if inserted_docs[self.name] else {}
                return {
                    "_id": "mongo-id",
                    "image_id": "img-1",
                    "result": latest.get("result", {"score": 0.9}),
                }
            return None

        def find(self, query):
            assert query == {"image_id": "img-1"}
            return self

        def sort(self, *_args, **_kwargs):
            return [{"_id": "1", "image_id": "img-1", "stage": "upload", "status": "done"}]

    class FakeDB:
        ai_results = FakeCollection("ai_results")
        image_metadata = FakeCollection("image_metadata")
        processing_logs = FakeCollection("processing_logs")

    monkeypatch.setattr(ai_mongo, "get_db", lambda: FakeDB())
    ai_mongo.ensure_indexes.cache_clear()

    assert ai_mongo.store_ai_result("img-1", {"score": 0.9}) == "ai_results-id"
    assert ai_mongo.store_image_metadata("img-1", {"Modality": "MRI"}) == "image_metadata-id"
    assert ai_mongo.store_processing_log("img-1", "upload", "done") == "processing_logs-id"
    assert ai_mongo.get_ai_result_by_image("img-1")["result"]["score"] == 0.9
    assert ai_mongo.get_ai_result_by_id("not-an-object-id") is None
    assert ai_mongo.get_processing_logs_by_image("img-1")[0]["_id"] == "1"
    assert created_indexes


def test_ai_mongo_returns_safe_defaults_on_driver_errors(monkeypatch):
    class BrokenCollection:
        def find_one(self, *_args, **_kwargs):
            raise ai_mongo.PyMongoError("broken")

        def find(self, *_args, **_kwargs):
            raise ai_mongo.PyMongoError("broken")

    class BrokenDB:
        ai_results = BrokenCollection()
        processing_logs = BrokenCollection()

    monkeypatch.setattr(ai_mongo, "get_db", lambda: BrokenDB())

    assert ai_mongo.get_ai_result_by_image("img-1") is None
    assert ai_mongo.get_processing_logs_by_image("img-1") == []


@pytest.mark.django_db
def test_report_api_success_and_edge_cases(monkeypatch):
    patient_user = User.objects.create_user(
        email="report-service-patient@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    patient_profile = PatientProfile.objects.create(user=patient_user)
    doctor_user = User.objects.create_user(
        email="report-service-doctor@example.com",
        password="StrongPass123",
        role=User.Role.DOCTOR,
    )
    doctor_profile = DoctorProfile.objects.create(user=doctor_user, specialty="Oncology")
    record = MedicalRecord.objects.create(
        patient=patient_profile,
        doctor=doctor_profile,
        diagnosis_text="Oncology review",
    )
    monkeypatch.setattr(
        "apps.reports.views.send_email_notification.delay",
        lambda *args, **kwargs: None,
    )

    doctor_client = APIClient()
    doctor_client.force_authenticate(user=doctor_user)
    create_response = doctor_client.post(
        "/reports/create",
        {"medical_record_id": str(record.id), "content": "Doctor draft"},
        format="json",
    )
    report = Report.objects.get(medical_record=record)

    assert create_response.status_code == 201

    missing_record = doctor_client.post(
        "/reports/create",
        {"medical_record_id": "00000000-0000-0000-0000-000000000000", "content": "Missing"},
        format="json",
    )
    assert missing_record.status_code == 404

    radiologist_user = User.objects.create_user(
        email="report-service-rad@example.com",
        password="StrongPass123",
        role=User.Role.RADIOLOGIST,
    )
    DoctorProfile.objects.create(user=radiologist_user, specialty="Radiology")
    rad_client = APIClient()
    rad_client.force_authenticate(user=radiologist_user)

    no_approve_response = rad_client.patch(
        f"/reports/{report.id}/approve",
        {"approve": False},
        format="json",
    )
    assert no_approve_response.status_code == 200
    report.refresh_from_db()
    assert report.status == Report.Status.DRAFT

    approve_response = rad_client.patch(
        f"/reports/{report.id}/approve",
        {"approve": True},
        format="json",
    )
    assert approve_response.status_code == 200
    report.refresh_from_db()
    assert report.status == Report.Status.APPROVED

    duplicate_approve = rad_client.patch(
        f"/reports/{report.id}/approve",
        {"approve": True},
        format="json",
    )
    missing_approve = rad_client.patch(
        "/reports/00000000-0000-0000-0000-000000000000/approve",
        {"approve": True},
        format="json",
    )

    assert duplicate_approve.status_code == 400
    assert missing_approve.status_code == 404

    patient_client = APIClient()
    patient_client.force_authenticate(user=patient_user)
    list_response = patient_client.get("/reports")
    download_response = patient_client.get(f"/reports/{report.id}/download")
    missing_download = patient_client.get("/reports/00000000-0000-0000-0000-000000000000/download")

    assert list_response.status_code == 200
    assert len(list_response.data) == 1
    assert download_response.status_code == 200
    assert missing_download.status_code == 404


@pytest.mark.django_db
def test_appointment_api_doctor_and_admin_listing_and_missing_status_update():
    patient_user = User.objects.create_user(
        email="appt-service-patient@example.com",
        password="StrongPass123",
        role=User.Role.PATIENT,
    )
    patient_profile = PatientProfile.objects.create(user=patient_user)
    doctor_user = User.objects.create_user(
        email="appt-service-doctor@example.com",
        password="StrongPass123",
        role=User.Role.DOCTOR,
    )
    doctor_profile = DoctorProfile.objects.create(user=doctor_user, specialty="General")
    appointment = Appointment.objects.create(
        patient=patient_profile,
        doctor=doctor_profile,
        scheduled_time="2030-01-01T10:00:00Z",
        reason="Visit",
    )
    admin_user = User.objects.create_user(
        email="appt-service-admin@example.com",
        password="StrongPass123",
        role=User.Role.ADMIN,
        is_staff=True,
    )

    doctor_client = APIClient()
    doctor_client.force_authenticate(user=doctor_user)
    doctor_list = doctor_client.get("/appointments")
    missing_update = doctor_client.patch(
        "/appointments/00000000-0000-0000-0000-000000000000/status",
        {"status": Appointment.Status.APPROVED},
        format="json",
    )

    admin_client = APIClient()
    admin_client.force_authenticate(user=admin_user)
    admin_list = admin_client.get("/appointments")

    assert doctor_list.status_code == 200
    assert doctor_list.data[0]["id"] == str(appointment.id)
    assert missing_update.status_code == 404
    assert admin_list.status_code == 200
    assert admin_list.data[0]["id"] == str(appointment.id)
