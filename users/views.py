from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .utils import is_patient, is_doctor


@login_required
def patient_dashboard(request):
    if not is_patient(request.user):
        return HttpResponse("Access Denied: Patients only", status=403)
    return HttpResponse("Welcome Patient Dashboard")


@login_required
def doctor_dashboard(request):
    if not is_doctor(request.user):
        return HttpResponse("Access Denied: Doctors only", status=403)
    return HttpResponse("Welcome Doctor Dashboard")
