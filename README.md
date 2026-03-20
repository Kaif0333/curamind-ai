# CuraMind AI

CuraMind AI is a HIPAA-aligned Telehealth & AI Diagnostic Platform featuring a Django core, FastAPI inference microservice, a Flask utility service, and Celery-based async processing.

## Architecture
- **Django**: Core API, auth, RBAC, medical records, imaging pipeline
- **FastAPI**: AI inference (ResNet50 example) and heatmap output
- **Flask**: Lightweight utility service for operational endpoints
- **Celery + Redis**: Background jobs (preprocess, inference, reports, notifications)
- **PostgreSQL**: Primary relational DB
- **MongoDB**: AI results, image metadata, and processing logs
- **S3**: Secure image storage with signed URLs

## Security Highlights
- DICOM uploads are de-identified before storage
- Medical image downloads are served through authenticated application endpoints
- Audit events are captured for image and report downloads

## Repository Structure
```text
curamind-ai/
+-- backend/
|   +-- django_core/
|   +-- ai_service_fastapi/
|   +-- celery_worker/
|   +-- flask_utils/
+-- apps/
|   +-- authentication/
|   +-- patients/
|   +-- doctors/
|   +-- appointments/
|   +-- medical_records/
|   +-- imaging/
|   +-- ai_engine/
|   +-- reports/
|   +-- audit_logs/
+-- infrastructure/
|   +-- docker/
|   +-- nginx/
+-- tests/
+-- scripts/
+-- docs/
```

## Local Setup
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Run Django
```bash
python backend/django_core/manage.py migrate
python backend/django_core/manage.py runserver
```

### Run FastAPI
```bash
uvicorn ai_service_fastapi.main:app --app-dir backend/ai_service_fastapi --reload --port 8001
```

### Run Flask Utilities
```bash
gunicorn --chdir . backend.flask_utils.app:app --bind 0.0.0.0:8002
```

### Run Celery
```bash
celery -A backend.celery_worker.celery_app worker -l info
```

## Docker
```bash
docker compose up -d --build
```

## Utility Endpoints
- `GET /utils/health`
- `GET /utils/version`

## Documentation
- `docs/deployment_guide.md`
- `docs/api.md`
