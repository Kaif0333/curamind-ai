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


class AppointmentCreateView(APIView):
    def get(self, request):
        user = request.user
        if user.role == User.Role.PATIENT:
            appointments = Appointment.objects.filter(patient=user.patient_profile)
        elif user.role == User.Role.DOCTOR:
            appointments = Appointment.objects.filter(doctor=user.doctor_profile)
        elif user.role in {User.Role.RADIOLOGIST, User.Role.ADMIN}:
            appointments = Appointment.objects.all()
        else:
            return Response({"detail": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)

        appointments = appointments.select_related("patient", "doctor").order_by("-scheduled_time")
        log_action(user, "appointment_view", request)
        return Response(
            AppointmentSerializer(appointments, many=True).data,
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        if request.user.role != User.Role.PATIENT:
            return Response({"detail": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)

        serializer = AppointmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doctor_id = serializer.validated_data["doctor_id"]
        scheduled_time = serializer.validated_data["scheduled_time"]
        reason = serializer.validated_data.get("reason", "")
        doctor = DoctorProfile.objects.filter(id=doctor_id, user__role=User.Role.DOCTOR).first()
        if not doctor:
            return Response({"detail": "Doctor not found"}, status=status.HTTP_404_NOT_FOUND)
        appointment = Appointment.objects.create(
            patient=request.user.patient_profile,
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

    def patch(self, request, appointment_id: str):
        appointment = Appointment.objects.filter(
            id=appointment_id, doctor=request.user.doctor_profile
        ).first()
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

    def patch(self, request, appointment_id: str):
        appointment = Appointment.objects.filter(
            id=appointment_id,
            patient=request.user.patient_profile,
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
