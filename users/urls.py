from django.urls import path
from . import views
from . import api_views

urlpatterns = [
    path('', views.role_redirect, name='users_home'),
    path('redirect/', views.role_redirect, name='role_redirect'),

    # patient
    path('patient/', views.patient_dashboard, name='patient_dashboard'),
    path('book/', views.book_appointment, name='book_appointment'),

    # doctor
    path('doctor/', views.doctor_dashboard, name='doctor_dashboard'),
    path('approve/<int:appointment_id>/', views.approve_appointment, name='approve_appointment'),
    path('reject/<int:appointment_id>/', views.reject_appointment, name='reject_appointment'),

    # api
    path('api/appointments/', api_views.AppointmentListCreateAPI.as_view(), name='api_appointments'),
    path('api/appointments/<int:appointment_id>/status/', api_views.AppointmentStatusUpdateAPI.as_view(), name='api_appointment_status'),
]
