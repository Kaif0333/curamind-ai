# CuraMind AI

CuraMind AI is a HIPAA-aligned Telehealth & AI Diagnostic Platform featuring a Django core, FastAPI inference microservice, and Celery-based async processing.

## Architecture
- **Django**: Core API, auth, RBAC, medical records, imaging pipeline
- **FastAPI**: AI inference (ResNet50 example) + heatmap output
- **Celery + Redis**: Background jobs (preprocess, inference, reports, notifications)
- **PostgreSQL**: Primary relational DB
- **MongoDB**: AI results + image metadata
- **S3**: Secure image storage with signed URLs

## Repository Structure
```
curamind-ai/
+-- backend/
¦   +-- django_core/
¦   +-- ai_service_fastapi/
¦   +-- celery_worker/
¦   +-- flask_utils/
+-- apps/
¦   +-- authentication/
¦   +-- patients/
¦   +-- doctors/
¦   +-- appointments/
¦   +-- medical_records/
¦   +-- imaging/
¦   +-- ai_engine/
¦   +-- reports/
¦   +-- audit_logs/
+-- infrastructure/
¦   +-- docker/
¦   +-- nginx/
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

### Run Celery
```bash
celery -A backend.celery_worker.celery_app worker -l info
```

## Docker
```bash
docker compose up -d --build
```

## Documentation
- `docs/deployment_guide.md`
- `docs/api.md`
