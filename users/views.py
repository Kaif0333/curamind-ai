from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from .models import User, Appointment


@login_required
def patient_dashboard(request):
    if request.user.user_type != "patient":
        return HttpResponseForbidden("You are not allowed")

    appointments = Appointment.objects.filter(patient=request.user)
    return render(request, "users/patient_dashboard.html", {
        "appointments": appointments
    })


@login_required
def create_appointment(request):
    if request.user.user_type != "patient":
        return HttpResponseForbidden("You are not allowed")

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

        return redirect("patient_dashboard")

    return render(request, "users/create_appointment.html", {
        "doctors": doctors
    })
