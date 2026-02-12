from django.urls import path
from . import views

urlpatterns = [
    path("redirect/", views.role_redirect),
    path("patient/", views.patient_dashboard),
    path("doctor/", views.doctor_dashboard),
    path("approve/<int:appointment_id>/", views.approve_appointment),
    path("reject/<int:appointment_id>/", views.reject_appointment),
]
