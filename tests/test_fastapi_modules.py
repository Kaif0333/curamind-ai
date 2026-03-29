from __future__ import annotations

import importlib
import sys
import types
from io import BytesIO

import numpy as np
import pytest
from PIL import Image

fake_cv2 = types.ModuleType("cv2")
setattr(fake_cv2, "COLOR_GRAY2RGB", 1)
setattr(fake_cv2, "IMREAD_COLOR", 2)
setattr(fake_cv2, "COLOR_BGR2RGB", 3)
setattr(fake_cv2, "COLOR_RGB2GRAY", 4)
setattr(fake_cv2, "COLORMAP_JET", 5)


def _fake_cvt_color(array, code):
    if code == fake_cv2.COLOR_GRAY2RGB:
        return np.stack([array, array, array], axis=-1)
    if code == fake_cv2.COLOR_BGR2RGB:
        return array[..., ::-1]
    if code == fake_cv2.COLOR_RGB2GRAY:
        return array.mean(axis=2).astype("uint8")
    return array


def _fake_imdecode(buffer, _flag):
    try:
        image = Image.open(BytesIO(bytes(buffer))).convert("RGB")
    except Exception:
        return None
    return np.array(image)[..., ::-1]


def _fake_apply_color_map(gray, _cmap):
    return np.stack([gray, gray, gray], axis=-1)


def _fake_imencode(_ext, array):
    image = Image.fromarray(array.astype("uint8"))
    output = BytesIO()
    image.save(output, format="PNG")
    return True, np.frombuffer(output.getvalue(), dtype=np.uint8)


setattr(fake_cv2, "cvtColor", _fake_cvt_color)
setattr(fake_cv2, "imdecode", _fake_imdecode)
setattr(fake_cv2, "applyColorMap", _fake_apply_color_map)
setattr(fake_cv2, "imencode", _fake_imencode)
sys.modules.setdefault("cv2", fake_cv2)


def _fastapi_utils_module():
    sys.modules.pop("backend.ai_service_fastapi.utils", None)
    return importlib.import_module("backend.ai_service_fastapi.utils")


def _fastapi_mongo_module():
    sys.modules.pop("backend.ai_service_fastapi.mongo", None)
    return importlib.import_module("backend.ai_service_fastapi.mongo")


def test_fastapi_utils_load_image_array_from_png_and_invalid_bytes():
    fastapi_utils = _fastapi_utils_module()
    image = Image.new("RGB", (2, 2), color=(10, 20, 30))
    buffer = BytesIO()
    image.save(buffer, format="PNG")

    array = fastapi_utils.load_image_array(buffer.getvalue())
    assert array.shape == (2, 2, 3)

    with pytest.raises(ValueError):
        fastapi_utils.load_image_array(b"not-an-image")


def test_fastapi_utils_normalize_to_uint8_handles_scaling_and_flat_arrays():
    fastapi_utils = _fastapi_utils_module()

    scaled = fastapi_utils.normalize_to_uint8(np.array([[10, 20]], dtype=np.uint16))
    flat = fastapi_utils.normalize_to_uint8(np.array([[5, 5]], dtype=np.int16))

    assert scaled.dtype == np.uint8
    assert scaled.min() == 0
    assert scaled.max() == 255
    assert np.array_equal(flat, np.zeros((1, 2), dtype=np.uint8))


def test_fastapi_utils_load_image_array_from_dicom(monkeypatch):
    fastapi_utils = _fastapi_utils_module()

    class FakeDataset:
        pixel_array = np.array([[0, 255]], dtype=np.uint8)

    fake_dataset = FakeDataset()

    monkeypatch.setattr(
        "backend.ai_service_fastapi.utils.pydicom.dcmread", lambda *_args: fake_dataset
    )

    array = fastapi_utils.load_image_array(b"dicom-bytes")

    assert array.shape[2] == 3


def test_fastapi_utils_create_heatmap_returns_base64_png():
    fastapi_utils = _fastapi_utils_module()
    array = np.zeros((2, 2, 3), dtype=np.uint8)
    result = fastapi_utils.create_heatmap(array)

    assert isinstance(result, str)
    assert result


def test_fastapi_mongo_get_ai_result(monkeypatch):
    fastapi_mongo = _fastapi_mongo_module()

    class FakeCollection:
        def find_one(self, query):
            if query == {"image_id": "img-1"}:
                return {"_id": "mongo-id", "result": {"score": 0.8}}
            return None

    class FakeDB:
        ai_results = FakeCollection()

    class FakeClient:
        def __getitem__(self, _name):
            return FakeDB()

    monkeypatch.setattr(fastapi_mongo, "_client", lambda: FakeClient())

    assert fastapi_mongo.get_ai_result("img-1") == {"score": 0.8}
    assert fastapi_mongo.get_ai_result("missing") is None


def test_fastapi_mongo_check_connection(monkeypatch):
    fastapi_mongo = _fastapi_mongo_module()

    class HealthyClient:
        class admin:
            @staticmethod
            def command(_name):
                return {"ok": 1}

    class BrokenClient:
        class admin:
            @staticmethod
            def command(_name):
                raise fastapi_mongo.PyMongoError("down")

    monkeypatch.setattr(fastapi_mongo, "_client", lambda: HealthyClient())
    assert fastapi_mongo.check_mongo_connection() is True

    monkeypatch.setattr(fastapi_mongo, "_client", lambda: BrokenClient())
    assert fastapi_mongo.check_mongo_connection() is False


def test_fastapi_model_predict_image_with_stubbed_ml_stack(monkeypatch):
    fake_torch = types.ModuleType("torch")

    class NoGradContext:
        def __enter__(self):
            return None

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeScalar:
        def item(self):
            return 0.25

    class FakeProbabilities:
        def max(self):
            return FakeScalar()

    setattr(fake_torch, "no_grad", lambda: NoGradContext())
    setattr(fake_torch, "softmax", lambda logits, dim=1: FakeProbabilities())

    fake_transforms = types.ModuleType("torchvision.transforms")

    class FakeTensor:
        def unsqueeze(self, _dim):
            return "tensor-batch"

    setattr(fake_transforms, "Resize", lambda size: ("resize", size))
    setattr(fake_transforms, "ToTensor", lambda: "to-tensor")
    setattr(
        fake_transforms,
        "Normalize",
        lambda mean, std: ("normalize", tuple(mean), tuple(std)),
    )
    setattr(fake_transforms, "Compose", lambda steps: (lambda image: FakeTensor()))

    fake_models = types.ModuleType("torchvision.models")

    class FakeModel:
        def eval(self):
            return self

        def __call__(self, tensor):
            return "logits"

    setattr(fake_models, "resnet50", lambda weights=None: FakeModel())

    fake_torchvision = types.ModuleType("torchvision")
    setattr(fake_torchvision, "transforms", fake_transforms)
    setattr(fake_torchvision, "models", fake_models)

    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    monkeypatch.setitem(sys.modules, "torchvision", fake_torchvision)
    monkeypatch.setitem(sys.modules, "torchvision.transforms", fake_transforms)
    monkeypatch.setitem(sys.modules, "torchvision.models", fake_models)

    module_name = "backend.ai_service_fastapi.model"
    sys.modules.pop(module_name, None)
    model_module = importlib.import_module(module_name)
    monkeypatch.setattr(
        model_module,
        "load_image_array",
        lambda image_bytes: np.zeros((2, 2, 3), dtype=np.uint8),
    )
    monkeypatch.setattr(model_module, "create_heatmap", lambda array: "heatmap-data")

    result = model_module.predict_image(b"image-bytes")

    assert result["model"] == "resnet50"
    assert result["model_version"] == "demo-resnet50-v1"
    assert result["device"] == "cpu"
    assert result["heatmap"] == "heatmap-data"
    assert result["anomaly_probability"] == 0.75


@pytest.mark.django_db
def test_doctor_profile_serializer_exposes_expected_fields():
    from apps.doctors.serializers import DoctorProfileSerializer
    from apps.doctors.models import DoctorProfile
    from apps.authentication.models import User

    user = User.objects.create_user(
        email="serializer-doctor@example.com",
        password="StrongPass123",
        role=User.Role.DOCTOR,
    )
    profile = DoctorProfile.objects.create(
        user=user,
        specialty="Radiology",
        license_number="LIC-123",
        phone="1234567890",
        department="Imaging",
    )

    data = DoctorProfileSerializer(profile).data

    assert str(data["id"]) == str(profile.id)
    assert str(data["user"]) == str(user.id)
    assert data["specialty"] == "Radiology"
