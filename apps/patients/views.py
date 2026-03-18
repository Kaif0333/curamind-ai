from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.permissions import IsPatient
from apps.patients.serializers import PatientProfileSerializer


class PatientProfileView(APIView):
    permission_classes = [IsPatient]

    def get(self, request):
        profile = request.user.patient_profile
        return Response(PatientProfileSerializer(profile).data, status=status.HTTP_200_OK)
