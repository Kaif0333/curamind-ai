from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.core.mail import send_mail

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Appointment, User
from .serializers import AppointmentSerializer


# 🔁 Redirect user based on role
@login_required
def role_redirect(request):
    user = request.user

    if user.user_type == "doctor":
        return redirect("/users/doctor/")
    elif user.user_type == "patient":
        return redirect("/users/patient/")
    else:
        return HttpResponse("Invalid user role")


# 🧑 PATIENT DASHBOARD
@login_required
def patient_dashboard(request):
    if request.user.user_type != "patient":
        return HttpResponse("Forbidden", status=403)

    appointments = Appointment.objects.filter(patient=request.user)
    doctors = User.objects.filter(user_type="doctor")

    if request.method == "POST":
        doctor_id = request.POST.get("doctor")
        date = request.POST.get("date")
        time = request.POST.get("time")

        Appointment.objects.create(
            patient=request.user,
            doctor_id=doctor_id,
            date=date,
            time=time
        )

        return redirect("/users/patient/")

    return render(
        request,
        "users/patient_dashboard.html",
        {
            "appointments": appointments,
            "doctors": doctors
        }
    )


# 🧑‍⚕️ DOCTOR DASHBOARD
@login_required
def doctor_dashboard(request):
    if request.user.user_type != "doctor":
        return HttpResponse("Forbidden", status=403)

    appointments = Appointment.objects.filter(doctor=request.user)

    return render(
        request,
        "users/doctor_dashboard.html",
        {
            "appointments": appointments
        }
    )


# ✅ APPROVE APPOINTMENT
@login_required
def approve_appointment(request, appointment_id):
    if request.user.user_type != "doctor":
        return HttpResponse("Forbidden", status=403)

    appointment = Appointment.objects.get(id=appointment_id)
    appointment.status = "approved"
    appointment.save()

    # 📧 Email notification (console backend)
    send_mail(
        subject="Appointment Approved",
        message=f"Your appointment with Dr. {request.user.username} has been approved.",
        from_email=None,
        recipient_list=[appointment.patient.email],
        fail_silently=True
    )

    return redirect("/users/doctor/")


# ❌ REJECT APPOINTMENT
@login_required
def reject_appointment(request, appointment_id):
    if request.user.user_type != "doctor":
        return HttpResponse("Forbidden", status=403)

    appointment = Appointment.objects.get(id=appointment_id)
    appointment.status = "rejected"
    appointment.save()

    # 📧 Email notification (console backend)
    send_mail(
        subject="Appointment Rejected",
        message=f"Your appointment with Dr. {request.user.username} has been rejected.",
        from_email=None,
        recipient_list=[appointment.patient.email],
        fail_silently=True
    )

    return redirect("/users/doctor/")


# 🌐 REST API – Appointments
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def appointments_api(request):
    user = request.user

    if user.user_type == "doctor":
        appointments = Appointment.objects.filter(doctor=user)
    else:
        appointments = Appointment.objects.filter(patient=user)

    serializer = AppointmentSerializer(appointments, many=True)
    return Response(serializer.data)
