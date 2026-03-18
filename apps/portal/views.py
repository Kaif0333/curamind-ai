from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpRequest
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.ai_engine.mongo import get_ai_result_by_image
from apps.appointments.models import Appointment
from apps.audit_logs.models import AuditLog
from apps.audit_logs.utils import log_action
from apps.authentication.models import LoginAttempt, User
from apps.authentication.views import LOGIN_ATTEMPT_TTL, MAX_LOGIN_ATTEMPTS, _attempt_key
from apps.doctors.models import DoctorProfile
from apps.imaging.models import MedicalImage
from apps.imaging.services import handle_image_upload
from apps.medical_records.models import MedicalRecord
from apps.notifications.tasks import send_email_notification
from apps.patients.models import PatientProfile
from apps.portal.forms import (
    AppointmentCreateForm,
    AppointmentStatusForm,
    ImageUploadForm,
    LoginForm,
    MedicalRecordCreateForm,
    RegisterForm,
    ReportApproveForm,
    ReportCreateForm,
)
from apps.reports.models import Report


def home(request: HttpRequest):
    if request.user.is_authenticated:
        return redirect("portal-dashboard")
    return render(request, "portal/home.html")


def login_view(request: HttpRequest):
    if request.user.is_authenticated:
        return redirect("portal-dashboard")

    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        attempt_key = _attempt_key(email, request.META.get("REMOTE_ADDR"))
        attempts = cache.get(attempt_key, 0)
        if attempts >= MAX_LOGIN_ATTEMPTS:
            messages.error(request, "Too many login attempts. Please try again later.")
            return render(request, "portal/login.html", {"form": form})

        user = form.authenticate_user()
        if user:
            cache.delete(attempt_key)
            login(request, user)
            LoginAttempt.objects.create(
                user=user,
                email=user.email,
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                success=True,
            )
            log_action(user, "login", request, resource_id=str(user.id))
            return redirect("portal-dashboard")
        cache.set(attempt_key, attempts + 1, timeout=LOGIN_ATTEMPT_TTL)
        LoginAttempt.objects.create(
            user=None,
            email=email,
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            success=False,
        )
        messages.error(request, "Invalid credentials")

    return render(request, "portal/login.html", {"form": form})


def logout_view(request: HttpRequest):
    if request.user.is_authenticated:
        log_action(request.user, "logout", request, resource_id=str(request.user.id))
    logout(request)
    return redirect("portal-home")


def register_view(request: HttpRequest):
    if request.user.is_authenticated:
        return redirect("portal-dashboard")

    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        role = form.cleaned_data["role"]
        user = User.objects.create_user(
            email=form.cleaned_data["email"],
            password=form.cleaned_data["password"],
            first_name=form.cleaned_data.get("first_name", ""),
            last_name=form.cleaned_data.get("last_name", ""),
            role=role,
        )
        if role == User.Role.PATIENT:
            PatientProfile.objects.create(user=user)
        elif role in {User.Role.DOCTOR, User.Role.RADIOLOGIST}:
            DoctorProfile.objects.create(user=user, specialty="")
        log_action(user, "register", request, resource_id=str(user.id))
        messages.success(request, "Account created. Please sign in.")
        return redirect("portal-login")

    return render(request, "portal/register.html", {"form": form})


def _render_dashboard(request: HttpRequest, template: str, context: dict):
    return render(request, template, context)


@login_required
def dashboard(request: HttpRequest):
    user = request.user

    if user.role == User.Role.PATIENT:
        patient = getattr(user, "patient_profile", None)
        appointments = Appointment.objects.filter(patient=patient).order_by("-scheduled_time")
        records = MedicalRecord.objects.filter(patient=patient).order_by("-created_at")
        reports = Report.objects.filter(medical_record__patient=patient).order_by("-created_at")
        images = MedicalImage.objects.filter(patient=patient).order_by("-uploaded_at")
        for image in images:
            image.ai_result = get_ai_result_by_image(str(image.id)) or {}
        context = {
            "appointments": appointments,
            "records": records,
            "reports": reports,
            "images": images,
            "appointment_form": AppointmentCreateForm(),
            "image_form": ImageUploadForm(),
        }
        return _render_dashboard(request, "portal/dashboard_patient.html", context)

    if user.role == User.Role.DOCTOR:
        doctor = getattr(user, "doctor_profile", None)
        appointments = Appointment.objects.filter(doctor=doctor).order_by("-scheduled_time")
        records = MedicalRecord.objects.filter(doctor=doctor).order_by("-created_at")
        reports = Report.objects.filter(author=user).order_by("-created_at")
        assigned_patients = (
            PatientProfile.objects.filter(
                Q(appointments__doctor=doctor) | Q(medical_records__doctor=doctor)
            )
            .select_related("user")
            .distinct()
        )
        context = {
            "appointments": appointments,
            "records": records,
            "reports": reports,
            "assigned_patients": assigned_patients,
            "appointment_status_form": AppointmentStatusForm(),
            "record_form": MedicalRecordCreateForm(user=user),
            "report_form": ReportCreateForm(user=user),
        }
        return _render_dashboard(request, "portal/dashboard_doctor.html", context)

    if user.role == User.Role.RADIOLOGIST:
        reports = Report.objects.filter(status=Report.Status.DRAFT).order_by("-created_at")
        context = {
            "reports": reports,
            "approve_form": ReportApproveForm(),
        }
        return _render_dashboard(request, "portal/dashboard_radiologist.html", context)

    context = {
        "user_count": User.objects.count(),
        "appointments": Appointment.objects.count(),
        "records": MedicalRecord.objects.count(),
        "reports": Report.objects.count(),
        "images": MedicalImage.objects.count(),
        "recent_audit_logs": AuditLog.objects.select_related("user")[:10],
    }
    return _render_dashboard(request, "portal/dashboard_admin.html", context)


@login_required
@require_POST
def book_appointment(request: HttpRequest):
    if request.user.role != User.Role.PATIENT:
        messages.error(request, "Not authorized")
        return redirect("portal-dashboard")

    form = AppointmentCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        appointment = form.save(commit=False)
        appointment.patient = request.user.patient_profile
        appointment.status = Appointment.Status.PENDING
        appointment.save()
        log_action(request.user, "appointment_create", request, resource_id=str(appointment.id))
        send_email_notification.delay(
            appointment.doctor.user.email,
            "New appointment request",
            f"New appointment scheduled by {request.user.email} on {appointment.scheduled_time}.",
        )
        messages.success(request, "Appointment requested")
    else:
        messages.error(request, "Unable to create appointment")
    return redirect("portal-dashboard")


@login_required
@require_POST
def upload_image(request: HttpRequest):
    if request.user.role != User.Role.PATIENT:
        messages.error(request, "Not authorized")
        return redirect("portal-dashboard")

    form = ImageUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        upload = form.cleaned_data["file"]
        modality = form.cleaned_data.get("modality", "")
        try:
            handle_image_upload(request.user, upload, request=request, modality=modality)
        except ValueError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, "Image uploaded")
    else:
        messages.error(request, "Invalid upload")
    return redirect("portal-dashboard")


@login_required
@require_POST
def update_appointment_status(request: HttpRequest, appointment_id: str):
    if request.user.role != User.Role.DOCTOR:
        messages.error(request, "Not authorized")
        return redirect("portal-dashboard")

    appointment = Appointment.objects.filter(
        id=appointment_id, doctor=request.user.doctor_profile
    ).first()
    if not appointment:
        messages.error(request, "Appointment not found")
        return redirect("portal-dashboard")

    form = AppointmentStatusForm(request.POST or None, instance=appointment)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_action(request.user, "appointment_update", request, resource_id=str(appointment.id))
        send_email_notification.delay(
            appointment.patient.user.email,
            "Appointment status updated",
            f"Your appointment status is now {appointment.status}.",
        )
        messages.success(request, "Appointment updated")
    else:
        messages.error(request, "Unable to update appointment")
    return redirect("portal-dashboard")


@login_required
@require_POST
def create_medical_record(request: HttpRequest):
    if request.user.role != User.Role.DOCTOR:
        messages.error(request, "Not authorized")
        return redirect("portal-dashboard")

    form = MedicalRecordCreateForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)
        record.doctor = request.user.doctor_profile
        record.save()
        log_action(request.user, "record_create", request, resource_id=str(record.id))
        messages.success(request, "Medical record created")
    else:
        messages.error(request, "Unable to create medical record")
    return redirect("portal-dashboard")


@login_required
@require_POST
def create_report(request: HttpRequest):
    if request.user.role != User.Role.DOCTOR:
        messages.error(request, "Not authorized")
        return redirect("portal-dashboard")

    form = ReportCreateForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        report = form.save(commit=False)
        report.author = request.user
        report.status = Report.Status.DRAFT
        report.save()
        log_action(request.user, "report_create", request, resource_id=str(report.id))
        send_email_notification.delay(
            report.medical_record.patient.user.email,
            "New report draft available",
            "A new medical report draft has been created for your record.",
        )
        messages.success(request, "Report created")
    else:
        messages.error(request, "Unable to create report")
    return redirect("portal-dashboard")


@login_required
@require_POST
def approve_report(request: HttpRequest, report_id: str):
    if request.user.role != User.Role.RADIOLOGIST:
        messages.error(request, "Not authorized")
        return redirect("portal-dashboard")

    report = Report.objects.filter(id=report_id).first()
    if not report:
        messages.error(request, "Report not found")
        return redirect("portal-dashboard")

    form = ReportApproveForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if report.status != Report.Status.DRAFT:
            messages.error(request, "Only draft reports can be approved")
            return redirect("portal-dashboard")
        report.status = Report.Status.APPROVED
        report.approved_at = timezone.now()
        report.save(update_fields=["status", "approved_at"])
        log_action(request.user, "report_approve", request, resource_id=str(report.id))
        send_email_notification.delay(
            report.medical_record.patient.user.email,
            "Report approved",
            "Your medical report has been approved by a radiologist.",
        )
        messages.success(request, "Report approved")
    else:
        messages.error(request, "Unable to approve report")
    return redirect("portal-dashboard")
