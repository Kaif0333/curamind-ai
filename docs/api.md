# API Documentation

## Django REST Endpoints
- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/refresh`
- `GET /appointments`
- `POST /appointments`
- `PATCH /appointments/<appointment_id>/cancel`
- `POST /upload-image`
- `GET /imaging/<image_id>/download`
- `GET /patient/records`
- `GET /doctor/patients`
- `GET /records/<record_id>/diagnoses`
- `POST /records/<record_id>/diagnoses`
- `GET /records/<record_id>/prescriptions`
- `POST /records/<record_id>/prescriptions`
- `GET /reports`
- `POST /reports/create`
- `GET /reports/<report_id>/download`
- `PATCH /reports/<report_id>/approve`
- `GET /audit-logs`
- `GET /ai/result?image_id=<id>`
- `GET /ai/logs?image_id=<id>`

## FastAPI Endpoints
- `POST /analyze-image`
- `GET /ai-result?image_id=<id>`

## Flask Utility Endpoints
- `GET /utils/health`
- `GET /utils/version`

## Notes
- All protected Django REST endpoints require JWT access tokens.
- Use `Authorization: Bearer <token>`.
- Rate limiting is enforced per user and IP.
- `GET /audit-logs` is restricted to admins.
- Medical image downloads are protected and no longer rely on public media URLs.
- DICOM uploads are de-identified before they are persisted.
