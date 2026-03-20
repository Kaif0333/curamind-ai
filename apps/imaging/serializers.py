from django.urls import reverse
from rest_framework import serializers

from apps.imaging.models import MedicalImage


class ImageUploadRequestSerializer(serializers.Serializer):
    file = serializers.FileField()
    modality = serializers.CharField(required=False, allow_blank=True)


class MedicalImageSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = MedicalImage
        fields = (
            "id",
            "patient",
            "uploaded_by",
            "file_name",
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
        path = reverse("image-download", kwargs={"image_id": obj.id})
        request = self.context.get("request")
        if request is None:
            return path
        return request.build_absolute_uri(path)
