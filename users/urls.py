from django.urls import path
from .views import patient_dashboard, create_appointment

urlpatterns = [
    path("patient/", patient_dashboard, name="patient_dashboard"),
    path("patient/appointment/", create_appointment, name="create_appointment"),
]
