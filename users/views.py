from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render


@login_required
def patient_dashboard(request):
    if request.user.role != "patient":
        return HttpResponseForbidden("You are not allowed to access this page")

    return render(request, "users/patient_dashboard.html")
