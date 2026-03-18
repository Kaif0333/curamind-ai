from __future__ import annotations

from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.permissions import IsPatient
from apps.imaging.serializers import MedicalImageSerializer
from apps.imaging.services import handle_image_upload


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
        return Response(MedicalImageSerializer(image).data, status=status.HTTP_201_CREATED)
