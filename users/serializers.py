from rest_framework import serializers
from .models import Appointment, User


class AppointmentSerializer(serializers.ModelSerializer):
    patient = serializers.CharField(source="patient.username", read_only=True)
    doctor = serializers.CharField(source="doctor.username", read_only=True)

    class Meta:
        model = Appointment
        fields = ["id", "patient", "doctor", "date", "time", "description", "status"]


class AppointmentCreateSerializer(serializers.ModelSerializer):
    doctor = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(user_type="doctor"))

    class Meta:
        model = Appointment
        fields = ["id", "doctor", "date", "time", "description"]

    def create(self, validated_data):
        return Appointment.objects.create(
            patient=self.context["request"].user,
            status="pending",
            **validated_data,
        )


class AppointmentStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = ["status"]

    def validate_status(self, value):
        if value not in ["approved", "rejected"]:
            raise serializers.ValidationError("Status must be approved or rejected.")
        return value
