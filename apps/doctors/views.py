from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.permissions import IsDoctor
from apps.patients.models import PatientProfile
from apps.patients.serializers import PatientProfileSerializer


class DoctorPatientsView(APIView):
    permission_classes = [IsDoctor]
    serializer_class = PatientProfileSerializer

    @extend_schema(responses=PatientProfileSerializer(many=True))
    def get(self, request):
        doctor_profile = getattr(request.user, "doctor_profile", None)
        if not doctor_profile:
            return Response(
                {"detail": "Doctor profile is not provisioned for this account."},
                status=status.HTTP_403_FORBIDDEN,
            )
        patients = (
            PatientProfile.objects.filter(
                Q(appointments__doctor=doctor_profile) | Q(medical_records__doctor=doctor_profile)
            )
            .select_related("user")
            .distinct()
        )
        data = PatientProfileSerializer(patients, many=True).data
        return Response(data, status=status.HTTP_200_OK)
