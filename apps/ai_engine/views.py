from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai_engine.mongo import get_ai_result_by_image, get_processing_logs_by_image
from apps.ai_engine.serializers import AIProcessingLogSerializer, AIResultSerializer
from apps.audit_logs.utils import log_action
from apps.imaging.access import get_authorized_image_for_user


class AIResultView(APIView):
    serializer_class = AIResultSerializer

    @extend_schema(
        parameters=[OpenApiParameter(name="image_id", required=True, type=str)],
        responses=AIResultSerializer,
    )
    def get(self, request):
        image_id = request.query_params.get("image_id")
        if not image_id:
            return Response({"detail": "image_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        image = get_authorized_image_for_user(request.user, image_id)
        if not image:
            return Response({"detail": "Image not found"}, status=status.HTTP_404_NOT_FOUND)

        result_doc = get_ai_result_by_image(str(image.id))
        if not result_doc:
            return Response({"detail": "AI result not found"}, status=status.HTTP_404_NOT_FOUND)

        log_action(request.user, "ai_result_view", request, resource_id=str(image.id))
        return Response(result_doc.get("result", {}), status=status.HTTP_200_OK)


class AIProcessingLogsView(APIView):
    serializer_class = AIProcessingLogSerializer

    @extend_schema(
        parameters=[OpenApiParameter(name="image_id", required=True, type=str)],
        responses=AIProcessingLogSerializer(many=True),
    )
    def get(self, request):
        image_id = request.query_params.get("image_id")
        if not image_id:
            return Response({"detail": "image_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        image = get_authorized_image_for_user(request.user, image_id)
        if not image:
            return Response({"detail": "Image not found"}, status=status.HTTP_404_NOT_FOUND)

        logs = get_processing_logs_by_image(str(image.id))
        log_action(request.user, "ai_processing_logs_view", request, resource_id=str(image.id))
        return Response(logs, status=status.HTTP_200_OK)
