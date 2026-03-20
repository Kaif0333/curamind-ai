from apps.appointments.models import Appointment
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai_engine.mongo import get_ai_result_by_image, get_processing_logs_by_image
from apps.audit_logs.utils import log_action
from apps.authentication.models import User
from apps.imaging.models import MedicalImage


def _get_authorized_image(user, image_id: str) -> MedicalImage | None:
    image = MedicalImage.objects.filter(id=image_id).select_related("patient__user").first()
    if not image:
        return None
    if user.role == User.Role.PATIENT and image.patient.user != user:
        return None
    if user.role == User.Role.DOCTOR:
        doctor_profile = getattr(user, "doctor_profile", None)
        if not doctor_profile or not (
            Appointment.objects.filter(doctor=doctor_profile, patient=image.patient).exists()
        ):
            return None
    if user.role == User.Role.NURSE:
        return None
    return image


class AIResultView(APIView):
    def get(self, request):
        image_id = request.query_params.get("image_id")
        if not image_id:
            return Response({"detail": "image_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        image = _get_authorized_image(request.user, image_id)
        if not image:
            return Response({"detail": "Image not found"}, status=status.HTTP_404_NOT_FOUND)

        result_doc = get_ai_result_by_image(str(image.id))
        if not result_doc:
            return Response({"detail": "AI result not found"}, status=status.HTTP_404_NOT_FOUND)

        log_action(request.user, "ai_result_view", request, resource_id=str(image.id))
        return Response(result_doc.get("result", {}), status=status.HTTP_200_OK)


class AIProcessingLogsView(APIView):
    def get(self, request):
        image_id = request.query_params.get("image_id")
        if not image_id:
            return Response({"detail": "image_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        image = _get_authorized_image(request.user, image_id)
        if not image:
            return Response({"detail": "Image not found"}, status=status.HTTP_404_NOT_FOUND)

        logs = get_processing_logs_by_image(str(image.id))
        log_action(request.user, "ai_processing_logs_view", request, resource_id=str(image.id))
        return Response(logs, status=status.HTTP_200_OK)
