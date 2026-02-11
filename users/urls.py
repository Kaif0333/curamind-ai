from django.urls import path
from .views import patient_dashboard, doctor_dashboard

urlpatterns = [
    path("patient/", patient_dashboard, name="patient_dashboard"),
    path("doctor/", doctor_dashboard, name="doctor_dashboard"),
]
