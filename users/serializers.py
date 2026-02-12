from rest_framework import serializers
from .models import Appointment


class AppointmentSerializer(serializers.ModelSerializer):
    patient = serializers.CharField(source="patient.username")
    doctor = serializers.CharField(source="doctor.username")

    class Meta:
        model = Appointment
        fields = ["id", "patient", "doctor", "date", "time", "status"]
