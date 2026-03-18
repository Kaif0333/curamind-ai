# API Documentation

## Django REST Endpoints
- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/refresh`
- `POST /upload-image`
- `GET /patient/records`
- `GET /doctor/patients`
- `POST /appointments`
- `GET /reports`
- `POST /reports/create`
- `PATCH /reports/<report_id>/approve`
- `GET /ai-result?image_id=<id>`

## FastAPI Endpoints
- `POST /analyze-image`
- `GET /ai-result?image_id=<id>`

## Notes
- All protected endpoints require JWT access tokens.
- Use `Authorization: Bearer <token>`.
- Rate limiting is enforced per user and IP.
