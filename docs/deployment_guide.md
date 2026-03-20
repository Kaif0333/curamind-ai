# Deployment Guide (AWS EC2 + Docker)

## Prerequisites
- AWS EC2 instance (Ubuntu recommended)
- Docker and Docker Compose installed
- Domain name and SSL certificates (Let's Encrypt or ACM)

## Steps
1. Clone the repository to the EC2 instance.
2. Copy `.env.example` to `.env` and fill in production values.
3. Build and start services:

```bash
docker compose up -d --build
```

4. Configure Nginx certificates:
- Mount certs into `/etc/nginx/certs/` as `fullchain.pem` and `privkey.pem`.

5. Verify services:
- Django: `http://<server>:8000/`
- FastAPI: `http://<server>:8001/`
- Flask utils: `http://<server>:8002/`
- Nginx: `http://<server>/`
- Utility endpoints via Nginx: `http://<server>/utils/health`

## Environment Variables
- `DJANGO_ENV=production`
- `DJANGO_SECRET_KEY=<secure random string>`
- `DATABASE_URL=postgres://...`
- `REDIS_URL=redis://...`
- `MONGO_URI=mongodb://...`
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `AWS_S3_BUCKET_NAME`
- `AI_SERVICE_URL=http://fastapi:8001`
- `MFA_ISSUER=CuraMind AI`
- `MFA_CHALLENGE_TTL=300`

## Security Notes
- Enforce HTTPS in production
- Use private S3 buckets with signed URLs
- Serve medical images through authenticated app endpoints rather than public media paths
- Keep DICOM de-identification enabled for all protected imaging uploads
- Rotate credentials regularly
