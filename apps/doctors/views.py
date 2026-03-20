from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.appointments.models import Appointment
from apps.authentication.permissions import IsDoctor
from apps.patients.serializers import PatientProfileSerializer


class DoctorPatientsView(APIView):
    permission_classes = [IsDoctor]
    serializer_class = PatientProfileSerializer

    @extend_schema(responses=PatientProfileSerializer(many=True))
    def get(self, request):
        doctor_profile = request.user.doctor_profile
        appointments = Appointment.objects.filter(doctor=doctor_profile).select_related("patient")
        patients = {appt.patient.id: appt.patient for appt in appointments}
        data = PatientProfileSerializer(list(patients.values()), many=True).data
        return Response(data, status=status.HTTP_200_OK)
