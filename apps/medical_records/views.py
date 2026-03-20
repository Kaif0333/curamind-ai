from apps.appointments.models import Appointment
from drf_spectacular.utils import extend_schema
from guardian.shortcuts import assign_perm
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit_logs.utils import log_action
from apps.authentication.models import User
from apps.authentication.permissions import IsDoctor, IsPatient
from apps.medical_records.models import Diagnosis, MedicalRecord, Prescription
from apps.medical_records.serializers import (
    DiagnosisCreateSerializer,
    DiagnosisSerializer,
    MedicalRecordCreateSerializer,
    MedicalRecordSerializer,
    PrescriptionCreateSerializer,
    PrescriptionSerializer,
)
from apps.patients.models import PatientProfile


def _get_record_for_user(user, record_id: str) -> MedicalRecord | None:
    record = (
        MedicalRecord.objects.filter(id=record_id)
        .select_related("patient__user", "doctor__user")
        .first()
    )
    if not record:
        return None
    if user.role == User.Role.PATIENT and record.patient.user != user:
        return None
    if user.role == User.Role.DOCTOR and record.doctor.user != user:
        return None
    if user.role not in {User.Role.PATIENT, User.Role.DOCTOR}:
        return None
    return record


class PatientRecordsView(APIView):
    permission_classes = [IsPatient]
    serializer_class = MedicalRecordSerializer

    @extend_schema(responses=MedicalRecordSerializer(many=True))
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
    serializer_class = MedicalRecordCreateSerializer

    @extend_schema(request=MedicalRecordCreateSerializer, responses=MedicalRecordSerializer)
    def post(self, request):
        serializer = MedicalRecordCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        patient = PatientProfile.objects.filter(id=serializer.validated_data["patient_id"]).first()
        if not patient:
            return Response({"detail": "Patient not found"}, status=status.HTTP_404_NOT_FOUND)
        doctor_profile = request.user.doctor_profile
        is_assigned_patient = (
            Appointment.objects.filter(doctor=doctor_profile, patient=patient).exists()
            or MedicalRecord.objects.filter(doctor=doctor_profile, patient=patient).exists()
        )
        if not is_assigned_patient:
            return Response(
                {"detail": "You can only create records for assigned patients."},
                status=status.HTTP_403_FORBIDDEN,
            )
        record = MedicalRecord.objects.create(
            patient=patient,
            doctor=doctor_profile,
            diagnosis_text=serializer.validated_data["diagnosis_text"],
            ai_analysis=serializer.validated_data.get("ai_analysis", {}),
        )
        assign_perm("view_medicalrecord", request.user, record)
        assign_perm("change_medicalrecord", request.user, record)
        assign_perm("view_medicalrecord", patient.user, record)
        log_action(request.user, "record_create", request, resource_id=str(record.id))
        return Response(MedicalRecordSerializer(record).data, status=status.HTTP_201_CREATED)


class RecordDiagnosesView(APIView):
    serializer_class = DiagnosisSerializer

    @extend_schema(responses=DiagnosisSerializer(many=True))
    def get(self, request, record_id: str):
        record = _get_record_for_user(request.user, record_id)
        if not record:
            return Response(
                {"detail": "Medical record not found"}, status=status.HTTP_404_NOT_FOUND
            )

        diagnoses = record.diagnoses.order_by("-created_at")
        log_action(request.user, "diagnosis_view", request, resource_id=record_id)
        return Response(DiagnosisSerializer(diagnoses, many=True).data, status=status.HTTP_200_OK)

    @extend_schema(request=DiagnosisCreateSerializer, responses=DiagnosisSerializer)
    def post(self, request, record_id: str):
        if request.user.role != User.Role.DOCTOR:
            return Response({"detail": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)

        record = _get_record_for_user(request.user, record_id)
        if not record:
            return Response(
                {"detail": "Medical record not found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = DiagnosisCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        diagnosis = Diagnosis.objects.create(
            medical_record=record,
            text=serializer.validated_data["text"],
        )
        log_action(request.user, "diagnosis_create", request, resource_id=str(diagnosis.id))
        return Response(DiagnosisSerializer(diagnosis).data, status=status.HTTP_201_CREATED)


class RecordPrescriptionsView(APIView):
    serializer_class = PrescriptionSerializer

    @extend_schema(responses=PrescriptionSerializer(many=True))
    def get(self, request, record_id: str):
        record = _get_record_for_user(request.user, record_id)
        if not record:
            return Response(
                {"detail": "Medical record not found"}, status=status.HTTP_404_NOT_FOUND
            )

        prescriptions = record.prescriptions.order_by("-created_at")
        log_action(request.user, "prescription_view", request, resource_id=record_id)
        return Response(
            PrescriptionSerializer(prescriptions, many=True).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(request=PrescriptionCreateSerializer, responses=PrescriptionSerializer)
    def post(self, request, record_id: str):
        if request.user.role != User.Role.DOCTOR:
            return Response({"detail": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)

        record = _get_record_for_user(request.user, record_id)
        if not record:
            return Response(
                {"detail": "Medical record not found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = PrescriptionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prescription = Prescription.objects.create(
            medical_record=record,
            medication_name=serializer.validated_data["medication_name"],
            dosage=serializer.validated_data["dosage"],
            instructions=serializer.validated_data.get("instructions", ""),
        )
        log_action(request.user, "prescription_create", request, resource_id=str(prescription.id))
        return Response(
            PrescriptionSerializer(prescription).data,
            status=status.HTTP_201_CREATED,
        )
