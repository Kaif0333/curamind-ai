# Deployment Guide (AWS EC2 + Docker)

## Prerequisites
- AWS EC2 instance (Ubuntu recommended)
- Docker and Docker Compose installed
- Domain name and SSL certificates (Let's Encrypt or ACM)

## Steps
1. Bootstrap the EC2 host:

```bash
sudo TARGET_USER=ubuntu APP_DIR=/opt/curamind-ai ./scripts/ec2_bootstrap.sh
```

2. Optional: provision the EC2, IAM, and CloudWatch foundation with Terraform:

```bash
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

3. Clone the repository to the EC2 instance.
4. Copy `.env.example` to `.env` and fill in production values.
5. Validate the production environment file:

```bash
./scripts/validate_production_env.sh .env
```

6. Install the CloudWatch agent:

```bash
sudo CLOUDWATCH_LOG_GROUP_PREFIX=/curamind/production ./scripts/install_cloudwatch_agent.sh
```

7. Build and start services:

```bash
docker compose up -d --build
```

8. Configure Nginx certificates:
- Mount certs into `/etc/nginx/certs/` as `fullchain.pem` and `privkey.pem`.

9. Verify services:
- Django direct: `http://<server>:8000/`
- FastAPI direct: `http://<server>:8001/`
- Flask utils direct: `http://<server>:8002/`
- Nginx: `http://<server>/`
- Health endpoints via Nginx:
  - `http://<server>/healthz`
  - `http://<server>/readyz`
  - `http://<server>/utils/health`
  - `http://<server>/ai/health`
  - `http://<server>/ai/ready`
  - `http://<server>/ai/model-info`

10. Run the post-deployment smoke check:

```bash
./scripts/post_deploy_healthcheck.sh https://your-domain-or-ip
```

11. Optional one-command deployment helper:

```bash
BASE_URL=https://your-domain-or-ip ./scripts/deploy_ec2.sh .env
```

## Environment Variables
- `DJANGO_ENV=production`
- `DJANGO_SECRET_KEY=<secure random string>`
- `DATABASE_URL=postgres://...`
- `REDIS_URL=redis://...`
- `MONGO_URI=mongodb://...`
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `AWS_S3_BUCKET_NAME`
- `AI_SERVICE_URL=http://fastapi:8001`
- `AI_MAX_UPLOAD_MB=25`
- `AI_MODEL_NAME=resnet50`
- `AI_MODEL_VERSION=demo-resnet50-v1`
- `AI_MODEL_REGISTRY=local-demo`
- `AI_MODEL_WEIGHTS_SHA256=<optional model checksum>`
- `AI_SERVICE_TIMEOUT_SECONDS=120`
- `AI_SERVICE_RETRY_COUNT=2`
- `AI_SERVICE_RETRY_BACKOFF_SECONDS=1`
- `IMAGE_PROCESSING_MAX_ATTEMPTS=3`
- `IMAGE_PROCESSING_RETRY_BACKOFF_SECONDS=2`
- `CELERY_TASK_TRACK_STARTED=True`
- `CELERY_TASK_ACKS_LATE=True`
- `CELERY_TASK_REJECT_ON_WORKER_LOST=True`
- `CELERY_WORKER_PREFETCH_MULTIPLIER=1`
- `CELERY_WORKER_MAX_TASKS_PER_CHILD=100`
- `CELERY_TASK_SOFT_TIME_LIMIT=240`
- `CELERY_TASK_TIME_LIMIT=300`
- `CLOUDWATCH_LOG_GROUP_PREFIX=/curamind/production`
- `BACKUP_RETENTION_DAYS=14`
- `MFA_ISSUER=CuraMind AI`
- `MFA_CHALLENGE_TTL=300`

## Security Notes
- Enforce HTTPS in production
- Use private S3 buckets with signed URLs
- Serve medical images through authenticated app endpoints rather than public media paths
- Keep DICOM de-identification enabled for all protected imaging uploads
- Rotate credentials regularly

## Operations Notes
- Docker Compose healthchecks gate service startup so Django, FastAPI, and Nginx wait for dependencies to become healthy.
- `/readyz` validates Django database and cache connectivity before marking the service ready.
- `/ai/ready` validates AI model warmup and MongoDB connectivity before marking inference ready.
- `/ai/model-info` now includes model registry/checksum metadata and upload constraints for easier deploy verification.
- AI result and metadata documents are upserted by `image_id` to avoid stale duplicate inference records.
- Use `scripts/backup_postgres.sh`, `scripts/restore_postgres.sh`, `scripts/backup_mongodb.sh`, and `scripts/restore_mongodb.sh` for operational backup workflows.
- Run `BACKUP_RETENTION_DAYS=14 ./scripts/prune_old_backups.sh` on a schedule so archives do not grow without bound.
- `infrastructure/aws/cloudwatch-agent-config.json` is the sample CloudWatch agent config used by `scripts/install_cloudwatch_agent.sh`.
- `infrastructure/terraform/` provisions EC2, IAM, CloudWatch log groups, and the security group foundation for the host.
