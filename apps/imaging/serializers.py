from rest_framework import serializers

from apps.imaging.models import MedicalImage
from apps.imaging.storage import S3StorageService


class MedicalImageSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = MedicalImage
        fields = (
            "id",
            "patient",
            "uploaded_by",
            "file_name",
            "s3_key",
            "modality",
            "content_type",
            "file_size",
            "metadata",
            "status",
            "uploaded_at",
            "download_url",
        )
        read_only_fields = ("id", "uploaded_at", "status", "download_url")

    def get_download_url(self, obj: MedicalImage) -> str:
        storage = S3StorageService()
        return storage.presigned_url(obj.s3_key)
