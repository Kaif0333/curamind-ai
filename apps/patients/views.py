from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.permissions import IsPatient
from apps.patients.serializers import PatientProfileSerializer


class PatientProfileView(APIView):
    permission_classes = [IsPatient]
    serializer_class = PatientProfileSerializer

    @extend_schema(responses=PatientProfileSerializer)
    def get(self, request):
        profile = getattr(request.user, "patient_profile", None)
        if not profile:
            return Response(
                {"detail": "Patient profile is not provisioned for this account."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(PatientProfileSerializer(profile).data, status=status.HTTP_200_OK)
