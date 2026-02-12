from django.urls import path
from . import views

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path("login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    path("redirect/", views.role_redirect),
    path("patient/", views.patient_dashboard),
    path("doctor/", views.doctor_dashboard),

    path("approve/<int:appointment_id>/", views.approve_appointment),
    path("reject/<int:appointment_id>/", views.reject_appointment),

    path("api/appointments/", views.appointments_api),
]
