from django.urls import path

from apps.patients.views import PatientProfileView

urlpatterns = [
    path("me", PatientProfileView.as_view(), name="patient-profile"),
]
