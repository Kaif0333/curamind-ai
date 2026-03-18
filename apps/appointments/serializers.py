from django.utils import timezone
from rest_framework import serializers

from apps.appointments.models import Appointment


class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = (
            "id",
            "patient",
            "doctor",
            "scheduled_time",
            "reason",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "status")


class AppointmentStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = ("status",)


class AppointmentCreateSerializer(serializers.Serializer):
    doctor_id = serializers.UUIDField()
    scheduled_time = serializers.DateTimeField()
    reason = serializers.CharField(required=False, allow_blank=True)

    def validate_scheduled_time(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("Appointments must be scheduled in the future.")
        return value
