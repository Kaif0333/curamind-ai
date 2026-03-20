from rest_framework import serializers

from apps.medical_records.models import Diagnosis, MedicalRecord, Prescription


class DiagnosisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Diagnosis
        fields = ("id", "text", "created_at")
        read_only_fields = ("id", "created_at")


class PrescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prescription
        fields = ("id", "medication_name", "dosage", "instructions", "created_at")
        read_only_fields = ("id", "created_at")


class MedicalRecordSerializer(serializers.ModelSerializer):
    diagnoses = DiagnosisSerializer(many=True, read_only=True)
    prescriptions = PrescriptionSerializer(many=True, read_only=True)

    class Meta:
        model = MedicalRecord
        fields = (
            "id",
            "patient",
            "doctor",
            "diagnosis_text",
            "ai_analysis",
            "created_at",
            "diagnoses",
            "prescriptions",
        )
        read_only_fields = ("id", "created_at")


class MedicalRecordCreateSerializer(serializers.Serializer):
    patient_id = serializers.UUIDField()
    diagnosis_text = serializers.CharField()
    ai_analysis = serializers.JSONField(required=False)


class DiagnosisCreateSerializer(serializers.Serializer):
    text = serializers.CharField()


class PrescriptionCreateSerializer(serializers.Serializer):
    medication_name = serializers.CharField(max_length=128)
    dosage = serializers.CharField(max_length=64)
    instructions = serializers.CharField(required=False, allow_blank=True)
