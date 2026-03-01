from datetime import date
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Appointment
from .serializers import (
    AppointmentSerializer,
    AppointmentCreateSerializer,
    AppointmentStatusSerializer,
)


class AppointmentListCreateAPI(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AppointmentSerializer

    def get_serializer_class(self):
        method = getattr(getattr(self, "request", None), "method", "GET")
        if method == "POST":
            return AppointmentCreateSerializer
        return AppointmentSerializer

    def get_queryset(self):
        user = self.request.user
        if user.user_type == "patient":
            queryset = Appointment.objects.filter(patient=user).order_by("-date", "-time")
        elif user.user_type == "doctor":
            queryset = Appointment.objects.filter(doctor=user).order_by("-date", "-time")
        else:
            queryset = Appointment.objects.none()

        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        if date_from:
            try:
                parsed_date_from = date.fromisoformat(date_from)
            except ValueError:
                return None
            queryset = queryset.filter(date__gte=parsed_date_from)
        if date_to:
            try:
                parsed_date_to = date.fromisoformat(date_to)
            except ValueError:
                return None
            queryset = queryset.filter(date__lte=parsed_date_to)

        return queryset

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if queryset is None:
            return Response(
                {"detail": "Invalid date format. Use YYYY-MM-DD for date_from/date_to."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = AppointmentSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = AppointmentSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        if request.user.user_type != "patient":
            return Response({"detail": "Only patients can create appointments."}, status=status.HTTP_403_FORBIDDEN)
        serializer = AppointmentCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        appointment = serializer.save()
        return Response(AppointmentSerializer(appointment).data, status=status.HTTP_201_CREATED)


class AppointmentStatusUpdateAPI(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AppointmentStatusSerializer

    def post(self, request, appointment_id, *args, **kwargs):
        if request.user.user_type != "doctor":
            return Response({"detail": "Only doctors can update appointment status."}, status=status.HTTP_403_FORBIDDEN)

        appointment = get_object_or_404(Appointment, id=appointment_id, doctor=request.user)
        if appointment.status != "pending":
            return Response({"detail": "Only pending appointments can be updated."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        appointment.status = serializer.validated_data["status"]
        appointment.save()
        return Response(AppointmentSerializer(appointment).data, status=status.HTTP_200_OK)
