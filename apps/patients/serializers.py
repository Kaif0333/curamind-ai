from rest_framework import serializers

from apps.patients.models import PatientProfile


class PatientProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientProfile
        fields = ("id", "user", "dob", "phone", "address", "emergency_contact", "created_at")
        read_only_fields = ("id", "created_at")
