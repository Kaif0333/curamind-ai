from rest_framework import serializers

from apps.doctors.models import DoctorProfile


class DoctorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorProfile
        fields = (
            "id",
            "user",
            "specialty",
            "license_number",
            "phone",
            "department",
            "created_at",
        )
        read_only_fields = ("id", "created_at")
