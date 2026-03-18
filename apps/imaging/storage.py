from __future__ import annotations

import uuid
from pathlib import Path

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings


class StorageError(Exception):
    pass


class S3StorageService:
    def __init__(self):
        self.bucket = settings.AWS_S3_PRIVATE_BUCKET
        self.region = settings.AWS_REGION
        self.use_s3 = bool(
            settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY and self.bucket
        )
        self.local_root = Path(settings.MEDIA_ROOT) / "uploads"
        self.local_root.mkdir(parents=True, exist_ok=True)
        if self.use_s3:
            self.client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=self.region,
                config=Config(signature_version="s3v4"),
            )
        else:
            self.client = None

    def build_key(self, filename: str) -> str:
        return f"medical-images/{uuid.uuid4()}-{filename}"

    def upload(self, file_obj, key: str) -> str:
        if self.use_s3:
            try:
                file_obj.seek(0)
                self.client.upload_fileobj(
                    file_obj,
                    self.bucket,
                    key,
                    ExtraArgs={"ServerSideEncryption": "AES256"},
                )
                return key
            except (BotoCoreError, ClientError) as exc:
                raise StorageError(str(exc)) from exc
        target = self.local_root / key.replace("/", "_")
        file_obj.seek(0)
        target.write_bytes(file_obj.read())
        return key

    def download(self, key: str) -> bytes:
        if self.use_s3:
            try:
                response = self.client.get_object(Bucket=self.bucket, Key=key)
                return response["Body"].read()
            except (BotoCoreError, ClientError) as exc:
                raise StorageError(str(exc)) from exc
        if Path(key).exists():
            return Path(key).read_bytes()
        target = self.local_root / key.replace("/", "_")
        return target.read_bytes()

    def presigned_url(self, key: str, expires: int = 3600) -> str:
        if not self.use_s3:
            return f"{settings.MEDIA_URL}uploads/{key.replace('/', '_')}"
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires,
        )
