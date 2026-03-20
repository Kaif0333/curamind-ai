from django.urls import path

from apps.appointments.views import (
    AppointmentCancelView,
    AppointmentCreateView,
    AppointmentStatusUpdateView,
)

urlpatterns = [
    path("", AppointmentCreateView.as_view(), name="appointment-create"),
    path(
        "<uuid:appointment_id>/cancel",
        AppointmentCancelView.as_view(),
        name="appointment-cancel",
    ),
    path(
        "<uuid:appointment_id>/status",
        AppointmentStatusUpdateView.as_view(),
        name="appointment-status",
    ),
]
