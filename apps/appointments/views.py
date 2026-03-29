from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.appointments.models import Appointment
from apps.appointments.serializers import (
    AppointmentCreateSerializer,
    AppointmentSerializer,
    AppointmentStatusSerializer,
)
from apps.audit_logs.utils import log_action
from apps.authentication.models import User
from apps.authentication.permissions import IsDoctor, IsPatient
from apps.doctors.models import DoctorProfile
from apps.notifications.tasks import send_email_notification


def _patient_profile_or_response(user):
    patient_profile = getattr(user, "patient_profile", None)
    if patient_profile:
        return patient_profile, None
    return None, Response(
        {"detail": "Patient profile is not provisioned for this account."},
        status=status.HTTP_403_FORBIDDEN,
    )


def _doctor_profile_or_response(user):
    doctor_profile = getattr(user, "doctor_profile", None)
    if doctor_profile:
        return doctor_profile, None
    return None, Response(
        {"detail": "Doctor profile is not provisioned for this account."},
        status=status.HTTP_403_FORBIDDEN,
    )


class AppointmentCreateView(APIView):
    serializer_class = AppointmentSerializer

    @extend_schema(responses=AppointmentSerializer(many=True))
    def get(self, request):
        user = request.user
        if user.role == User.Role.PATIENT:
            patient_profile, error = _patient_profile_or_response(user)
            if error:
                return error
            appointments = Appointment.objects.filter(patient=patient_profile)
        elif user.role == User.Role.DOCTOR:
            doctor_profile, error = _doctor_profile_or_response(user)
            if error:
                return error
            appointments = Appointment.objects.filter(doctor=doctor_profile)
        elif user.role == User.Role.ADMIN:
            appointments = Appointment.objects.all()
        else:
            return Response({"detail": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)

        appointments = appointments.select_related("patient", "doctor").order_by("-scheduled_time")
        log_action(user, "appointment_view", request)
        return Response(
            AppointmentSerializer(appointments, many=True).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(request=AppointmentCreateSerializer, responses=AppointmentSerializer)
    def post(self, request):
        if request.user.role != User.Role.PATIENT:
            return Response({"detail": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)
        patient_profile, error = _patient_profile_or_response(request.user)
        if error:
            return error

        serializer = AppointmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doctor_id = serializer.validated_data["doctor_id"]
        scheduled_time = serializer.validated_data["scheduled_time"]
        reason = serializer.validated_data.get("reason", "")
        doctor = DoctorProfile.objects.filter(id=doctor_id, user__role=User.Role.DOCTOR).first()
        if not doctor:
            return Response({"detail": "Doctor not found"}, status=status.HTTP_404_NOT_FOUND)
        appointment = Appointment.objects.create(
            patient=patient_profile,
            doctor=doctor,
            scheduled_time=scheduled_time,
            reason=reason,
        )
        log_action(request.user, "appointment_create", request, resource_id=str(appointment.id))
        send_email_notification.delay(
            doctor.user.email,
            "New appointment request",
            f"New appointment scheduled by {request.user.email} on {scheduled_time}.",
        )
        return Response(AppointmentSerializer(appointment).data, status=status.HTTP_201_CREATED)


class AppointmentStatusUpdateView(APIView):
    permission_classes = [IsDoctor]
    serializer_class = AppointmentStatusSerializer

    @extend_schema(request=AppointmentStatusSerializer, responses=AppointmentSerializer)
    def patch(self, request, appointment_id: str):
        doctor_profile, error = _doctor_profile_or_response(request.user)
        if error:
            return error
        appointment = Appointment.objects.filter(id=appointment_id, doctor=doctor_profile).first()
        if not appointment:
            return Response({"detail": "Appointment not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = AppointmentStatusSerializer(appointment, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_action(request.user, "appointment_update", request, resource_id=str(appointment.id))
        send_email_notification.delay(
            appointment.patient.user.email,
            "Appointment status updated",
            f"Your appointment status is now {appointment.status}.",
        )
        return Response(AppointmentSerializer(appointment).data, status=status.HTTP_200_OK)


class AppointmentCancelView(APIView):
    permission_classes = [IsPatient]
    serializer_class = AppointmentSerializer

    @extend_schema(responses=AppointmentSerializer)
    def patch(self, request, appointment_id: str):
        patient_profile, error = _patient_profile_or_response(request.user)
        if error:
            return error
        appointment = Appointment.objects.filter(
            id=appointment_id,
            patient=patient_profile,
        ).first()
        if not appointment:
            return Response({"detail": "Appointment not found"}, status=status.HTTP_404_NOT_FOUND)
        if appointment.status in {
            Appointment.Status.CANCELLED,
            Appointment.Status.COMPLETED,
            Appointment.Status.REJECTED,
        }:
            return Response(
                {"detail": "Appointment can no longer be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        appointment.status = Appointment.Status.CANCELLED
        appointment.save(update_fields=["status", "updated_at"])
        log_action(request.user, "appointment_cancel", request, resource_id=str(appointment.id))
        send_email_notification.delay(
            appointment.doctor.user.email,
            "Appointment cancelled",
            (
                f"{request.user.email} cancelled the appointment scheduled "
                f"for {appointment.scheduled_time}."
            ),
        )
        return Response(AppointmentSerializer(appointment).data, status=status.HTTP_200_OK)
