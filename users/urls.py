from django.urls import path
from . import views

urlpatterns = [
    path('redirect/', views.role_redirect, name='role_redirect'),

    # patient
    path('patient/', views.patient_dashboard, name='patient_dashboard'),
    path('book/', views.book_appointment, name='book_appointment'),

    # doctor
    path('doctor/', views.doctor_dashboard, name='doctor_dashboard'),
    path('approve/<int:appointment_id>/', views.approve_appointment, name='approve_appointment'),
    path('reject/<int:appointment_id>/', views.reject_appointment, name='reject_appointment'),
]
