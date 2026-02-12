from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .models import Appointment


@login_required
def role_redirect(request):
    user = request.user

    if user.user_type == "doctor":
        return redirect("/users/doctor/")
    elif user.user_type == "patient":
        return redirect("/users/patient/")
    else:
        return HttpResponse("Invalid user role")


@login_required
def doctor_dashboard(request):
    if request.user.user_type != "doctor":
        return HttpResponse("Forbidden", status=403)

    appointments = Appointment.objects.filter(doctor=request.user)

    return render(request, "users/doctor_dashboard.html", {
        "appointments": appointments
    })


@login_required
def approve_appointment(request, appointment_id):
    if request.user.user_type != "doctor":
        return HttpResponse("Forbidden", status=403)

    appointment = Appointment.objects.get(id=appointment_id)
    appointment.status = "approved"
    appointment.save()

    return redirect("/users/doctor/")


@login_required
def reject_appointment(request, appointment_id):
    if request.user.user_type != "doctor":
        return HttpResponse("Forbidden", status=403)

    appointment = Appointment.objects.get(id=appointment_id)
    appointment.status = "rejected"
    appointment.save()

    return redirect("/users/doctor/")
