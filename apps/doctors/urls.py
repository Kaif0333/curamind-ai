from django.urls import path

from apps.doctors.views import DoctorPatientsView

urlpatterns = [
    path("patients", DoctorPatientsView.as_view(), name="doctor-patients"),
]
