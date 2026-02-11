from django.urls import path
from .views import patient_dashboard

app_name = "users"

urlpatterns = [
    path("patient/", patient_dashboard, name="patient_dashboard"),
]
