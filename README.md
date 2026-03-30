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
- TOTP-based MFA setup and login verification for API and portal accounts
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

Docker Compose now includes service healthchecks for PostgreSQL, MongoDB, Redis, Django, FastAPI, Flask utils, and Nginx so startup ordering is more reliable.

## Health Endpoints
- `GET /healthz` - Django liveness
- `GET /readyz` - Django readiness (database + cache)
- `GET /utils/health` - Flask utility service health
- `GET /utils/version` - Flask utility service version
- `GET /ai/health` - FastAPI AI service liveness
- `GET /ai/ready` - FastAPI AI service readiness (model + MongoDB)
- `GET /ai/model-info` - FastAPI AI model metadata

## AWS / Ops Helpers
- `scripts/ec2_bootstrap.sh` installs Docker, Docker Compose, and prepares an Ubuntu EC2 host
- `scripts/validate_production_env.sh` verifies required production env vars and secure settings
- `scripts/deploy_ec2.sh` builds, starts, and smoke-checks the stack on an EC2 host
- `scripts/install_cloudwatch_agent.sh` installs and starts the CloudWatch agent on Ubuntu EC2
- `scripts/backup_postgres.sh` and `scripts/restore_postgres.sh` back up and restore PostgreSQL
- `scripts/backup_mongodb.sh` and `scripts/restore_mongodb.sh` back up and restore MongoDB
- `scripts/prune_old_backups.sh` removes backup archives older than the configured retention window
- `scripts/post_deploy_healthcheck.sh` runs a post-deployment smoke check against the key health endpoints
- `infrastructure/terraform/` contains the AWS IaC scaffold for EC2, IAM, CloudWatch, and security groups

## Deployment Configuration
- `docker compose` reads overrides from `.env`
- AI service knobs:
  - `AI_MAX_UPLOAD_MB`
  - `AI_MODEL_NAME`
  - `AI_MODEL_VERSION`
  - `AI_MODEL_REGISTRY`
  - `AI_MODEL_WEIGHTS_SHA256`
  - `AI_SERVICE_TIMEOUT_SECONDS`
  - `AI_SERVICE_RETRY_COUNT`
  - `AI_SERVICE_RETRY_BACKOFF_SECONDS`
  - `IMAGE_PROCESSING_MAX_ATTEMPTS`
  - `IMAGE_PROCESSING_RETRY_BACKOFF_SECONDS`
- Celery worker knobs:
  - `CELERY_TASK_TRACK_STARTED`
  - `CELERY_TASK_ACKS_LATE`
  - `CELERY_TASK_REJECT_ON_WORKER_LOST`
  - `CELERY_WORKER_PREFETCH_MULTIPLIER`
  - `CELERY_WORKER_MAX_TASKS_PER_CHILD`
  - `CELERY_TASK_SOFT_TIME_LIMIT`
  - `CELERY_TASK_TIME_LIMIT`
- Django upload validation knob:
  - `MAX_UPLOAD_MB`
- Backup retention knob:
  - `BACKUP_RETENTION_DAYS`

## Documentation
- `docs/deployment_guide.md`
- `docs/api.md`
