from __future__ import annotations

from io import BytesIO
from typing import Any

import pydicom
from pydicom.errors import InvalidDicomError

ALLOWED_MIME_TYPES = {
    "application/dicom",
    "application/dicom+xml",
    "image/jpeg",
    "image/png",
    "image/jpg",
}

PHI_TAGS = {
    "PatientName",
    "PatientID",
    "PatientBirthDate",
    "PatientSex",
    "PatientAge",
    "PatientAddress",
    "PatientTelephoneNumbers",
}


def is_dicom_upload(filename: str, content_type: str) -> bool:
    normalized_name = filename.lower()
    normalized_type = (content_type or "").lower()
    return normalized_name.endswith(".dcm") or normalized_type in {
        "application/dicom",
        "application/dicom+xml",
        "application/octet-stream",
    }


def validate_upload(
    filename: str,
    content_type: str,
    file_size: int,
    max_size_mb: int,
) -> None:
    normalized_type = (content_type or "").lower()
    if normalized_type not in ALLOWED_MIME_TYPES and not is_dicom_upload(filename, normalized_type):
        raise ValueError("Unsupported file type")
    if file_size > max_size_mb * 1024 * 1024:
        raise ValueError("File size exceeds limit")


def extract_dicom_metadata(file_bytes: bytes) -> dict[str, Any]:
    try:
        dataset = pydicom.dcmread(BytesIO(file_bytes), stop_before_pixels=True)
    except InvalidDicomError as exc:
        raise ValueError("Invalid DICOM file") from exc
    metadata = {elem.keyword: str(elem.value) for elem in dataset if elem.keyword}
    return sanitize_dicom_metadata(metadata)


def sanitize_dicom_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    for tag in PHI_TAGS:
        metadata.pop(tag, None)
    return metadata
