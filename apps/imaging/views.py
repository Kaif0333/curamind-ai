from __future__ import annotations

from django.http import FileResponse, HttpResponseRedirect
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit_logs.utils import log_action
from apps.authentication.permissions import IsPatient
from apps.imaging.access import get_authorized_image_for_user
from apps.imaging.serializers import MedicalImageSerializer
from apps.imaging.services import handle_image_upload
from apps.imaging.storage import S3StorageService


class ImageUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsPatient]

    def post(self, request):
        upload = request.FILES.get("file")
        if not upload:
            return Response({"detail": "File is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            image = handle_image_upload(
                request.user,
                upload,
                request=request,
                modality=request.data.get("modality", ""),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = MedicalImageSerializer(image, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ImageDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, image_id: str):
        image = get_authorized_image_for_user(request.user, image_id)
        if not image:
            return Response({"detail": "Image not found"}, status=status.HTTP_404_NOT_FOUND)

        storage = S3StorageService()
        log_action(request.user, "image_download", request, resource_id=str(image.id))

        if storage.use_s3:
            return HttpResponseRedirect(storage.presigned_url(image.s3_key))

        response = FileResponse(
            storage.open_file(image.s3_key),
            content_type=image.content_type,
            as_attachment=True,
            filename=image.file_name,
        )
        return response
