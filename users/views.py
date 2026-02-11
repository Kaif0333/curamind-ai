from django.shortcuts import render
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required


@login_required
def patient_dashboard(request):
    if request.user.role != "patient":
        return HttpResponseForbidden("You are not allowed to access this page")

    return render(request, "users/patient_dashboard.html")


@login_required
def doctor_dashboard(request):
    if request.user.role != "doctor":
        return HttpResponseForbidden("You are not allowed to access this page")

    return render(request, "users/doctor_dashboard.html")
