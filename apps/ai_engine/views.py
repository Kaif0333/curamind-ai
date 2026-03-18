from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai_engine.mongo import get_ai_result_by_image
from apps.audit_logs.utils import log_action
from apps.authentication.models import User
from apps.imaging.models import MedicalImage


class AIResultView(APIView):
    def get(self, request):
        image_id = request.query_params.get("image_id")
        if not image_id:
            return Response({"detail": "image_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        image = MedicalImage.objects.filter(id=image_id).select_related("patient").first()
        if not image:
            return Response({"detail": "Image not found"}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if user.role == User.Role.PATIENT and image.patient.user != user:
            return Response({"detail": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)

        result_doc = get_ai_result_by_image(str(image.id))
        if not result_doc:
            return Response({"detail": "AI result not found"}, status=status.HTTP_404_NOT_FOUND)

        log_action(user, "ai_result_view", request, resource_id=str(image.id))
        return Response(result_doc.get("result", {}), status=status.HTTP_200_OK)
