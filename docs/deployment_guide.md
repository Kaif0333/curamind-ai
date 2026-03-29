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

2. Clone the repository to the EC2 instance.
3. Copy `.env.example` to `.env` and fill in production values.
4. Build and start services:

```bash
docker compose up -d --build
```

5. Configure Nginx certificates:
- Mount certs into `/etc/nginx/certs/` as `fullchain.pem` and `privkey.pem`.

6. Verify services:
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

7. Run the post-deployment smoke check:

```bash
./scripts/post_deploy_healthcheck.sh https://your-domain-or-ip
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
