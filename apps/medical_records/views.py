from guardian.shortcuts import assign_perm
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit_logs.utils import log_action
from apps.authentication.permissions import IsDoctor, IsPatient
from apps.medical_records.models import MedicalRecord
from apps.medical_records.serializers import MedicalRecordCreateSerializer, MedicalRecordSerializer
from apps.patients.models import PatientProfile


class PatientRecordsView(APIView):
    permission_classes = [IsPatient]

    def get(self, request):
        records = (
            MedicalRecord.objects.filter(patient=request.user.patient_profile)
            .select_related("patient", "doctor")
            .order_by("-created_at")
        )
        log_action(request.user, "record_view", request)
        return Response(MedicalRecordSerializer(records, many=True).data, status=status.HTTP_200_OK)


class MedicalRecordCreateView(APIView):
    permission_classes = [IsDoctor]

    def post(self, request):
        serializer = MedicalRecordCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        patient = PatientProfile.objects.filter(id=serializer.validated_data["patient_id"]).first()
        if not patient:
            return Response({"detail": "Patient not found"}, status=status.HTTP_404_NOT_FOUND)
        record = MedicalRecord.objects.create(
            patient=patient,
            doctor=request.user.doctor_profile,
            diagnosis_text=serializer.validated_data["diagnosis_text"],
            ai_analysis=serializer.validated_data.get("ai_analysis", {}),
        )
        assign_perm("view_medicalrecord", request.user, record)
        assign_perm("change_medicalrecord", request.user, record)
        assign_perm("view_medicalrecord", patient.user, record)
        log_action(request.user, "record_create", request, resource_id=str(record.id))
        return Response(MedicalRecordSerializer(record).data, status=status.HTTP_201_CREATED)
