from django.urls import path

from apps.appointments.views import AppointmentCreateView, AppointmentStatusUpdateView

urlpatterns = [
    path("", AppointmentCreateView.as_view(), name="appointment-create"),
    path(
        "<uuid:appointment_id>/status",
        AppointmentStatusUpdateView.as_view(),
        name="appointment-status",
    ),
]
