from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.http import FileResponse, HttpRequest, HttpResponse, HttpResponseRedirect
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.ai_engine.mongo import get_ai_result_by_image
from apps.appointments.models import Appointment
from apps.audit_logs.models import AuditLog
from apps.audit_logs.utils import log_action
from apps.authentication.mfa import build_mfa_provisioning_uri, generate_mfa_secret, verify_mfa_code
from apps.authentication.models import LoginAttempt, User
from apps.authentication.serializers import RegisterSerializer
from apps.authentication.views import LOGIN_ATTEMPT_TTL, MAX_LOGIN_ATTEMPTS, _attempt_key
from apps.imaging.access import get_authorized_image_for_user
from apps.imaging.models import MedicalImage
from apps.imaging.services import handle_image_upload
from apps.imaging.storage import S3StorageService
from apps.medical_records.models import MedicalRecord
from apps.notifications.tasks import send_email_notification
from apps.patients.models import PatientProfile
from apps.portal.forms import (
    AppointmentCancelForm,
    AppointmentCreateForm,
    AppointmentStatusForm,
    DiagnosisCreateForm,
    ImageUploadForm,
    LoginForm,
    MFADisableForm,
    MFALoginForm,
    MedicalRecordCreateForm,
    PrescriptionCreateForm,
    RegisterForm,
    ReportApproveForm,
    ReportCreateForm,
)
from apps.reports.models import Report

PENDING_PORTAL_MFA_USER_ID = "pending_portal_mfa_user_id"
PENDING_PORTAL_MFA_BACKEND = "pending_portal_mfa_backend"


def _flash_form_errors(request: HttpRequest, form, fallback_message: str) -> None:
    form_errors: list[str] = []
    for field, errors in form.errors.items():
        if field == "__all__":
            form_errors.extend(str(error) for error in errors)
            continue
        label = form.fields[field].label or field.replace("_", " ").title()
        form_errors.extend(f"{label}: {error}" for error in errors)

    if not form_errors:
        messages.error(request, fallback_message)
        return

    for error in form_errors:
        messages.error(request, error)


def _get_pending_portal_mfa_user(pending_user_id: str | None) -> User | None:
    if not pending_user_id:
        return None
    try:
        return User.objects.filter(id=pending_user_id).first()
    except (ValidationError, ValueError, TypeError):
        return None


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
            if user.mfa_enabled:
                request.session[PENDING_PORTAL_MFA_USER_ID] = str(user.id)
                request.session[PENDING_PORTAL_MFA_BACKEND] = getattr(
                    user,
                    "backend",
                    "django.contrib.auth.backends.ModelBackend",
                )
                log_action(user, "login_mfa_challenge", request, resource_id=str(user.id))
                messages.info(request, "Enter your authentication code to finish signing in.")
                return redirect("portal-mfa-login")
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


def mfa_login_view(request: HttpRequest):
    if request.user.is_authenticated:
        return redirect("portal-dashboard")

    pending_user_id = request.session.get(PENDING_PORTAL_MFA_USER_ID)
    if not pending_user_id:
        messages.error(request, "No pending MFA challenge. Please sign in again.")
        return redirect("portal-login")

    form = MFALoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = _get_pending_portal_mfa_user(pending_user_id)
        if not user:
            request.session.pop(PENDING_PORTAL_MFA_USER_ID, None)
            request.session.pop(PENDING_PORTAL_MFA_BACKEND, None)
            messages.error(request, "MFA challenge expired. Please sign in again.")
            return redirect("portal-login")
        if not verify_mfa_code(user, form.cleaned_data["code"]):
            LoginAttempt.objects.create(
                user=user,
                email=user.email,
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                success=False,
            )
            messages.error(request, "Invalid authentication code.")
            return render(request, "portal/login_mfa.html", {"form": form, "email": user.email})

        request.session.pop(PENDING_PORTAL_MFA_USER_ID, None)
        backend = request.session.pop(
            PENDING_PORTAL_MFA_BACKEND,
            "django.contrib.auth.backends.ModelBackend",
        )
        login(request, user, backend=backend)
        LoginAttempt.objects.create(
            user=user,
            email=user.email,
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            success=True,
        )
        log_action(user, "login", request, resource_id=str(user.id))
        return redirect("portal-dashboard")

    email = ""
    user = _get_pending_portal_mfa_user(pending_user_id)
    if user:
        email = user.email
    else:
        request.session.pop(PENDING_PORTAL_MFA_USER_ID, None)
        request.session.pop(PENDING_PORTAL_MFA_BACKEND, None)
        messages.error(request, "MFA challenge expired. Please sign in again.")
        return redirect("portal-login")
    return render(request, "portal/login_mfa.html", {"form": form, "email": email})


def logout_view(request: HttpRequest):
    if request.user.is_authenticated:
        log_action(request.user, "logout", request, resource_id=str(request.user.id))
    logout(request)
    request.session.pop(PENDING_PORTAL_MFA_USER_ID, None)
    request.session.pop(PENDING_PORTAL_MFA_BACKEND, None)
    return redirect("portal-home")


def register_view(request: HttpRequest):
    if request.user.is_authenticated:
        return redirect("portal-dashboard")

    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        serializer = RegisterSerializer(
            data={
                "email": form.cleaned_data["email"],
                "password": form.cleaned_data["password"],
                "first_name": form.cleaned_data.get("first_name", ""),
                "last_name": form.cleaned_data.get("last_name", ""),
                "role": form.cleaned_data["role"],
            }
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        log_action(user, "register", request, resource_id=str(user.id))
        messages.success(request, "Account created. Please sign in.")
        return redirect("portal-login")

    return render(request, "portal/register.html", {"form": form})


def _render_dashboard(request: HttpRequest, template: str, context: dict):
    return render(request, template, context)


def _render_account_issue(request: HttpRequest, role_label: str, issue_message: str):
    return render(
        request,
        "portal/dashboard_account_issue.html",
        {"role_label": role_label, "issue_message": issue_message},
    )


@login_required
def mfa_settings_view(request: HttpRequest):
    user = request.user
    provisioning_uri = build_mfa_provisioning_uri(user, user.mfa_secret) if user.mfa_secret else ""
    verify_form = MFALoginForm()
    disable_form = MFADisableForm()

    if request.method == "POST":
        action = request.POST.get("action", "")
        if action == "start":
            user.mfa_secret = generate_mfa_secret()
            user.mfa_enabled = False
            user.save(update_fields=["mfa_secret", "mfa_enabled"])
            provisioning_uri = build_mfa_provisioning_uri(user, user.mfa_secret)
            log_action(user, "mfa_setup_started", request, resource_id=str(user.id))
            messages.success(
                request, "MFA setup started. Add the secret to your authenticator and verify."
            )
            return render(
                request,
                "portal/security_mfa.html",
                {
                    "provisioning_uri": provisioning_uri,
                    "verify_form": verify_form,
                    "disable_form": disable_form,
                },
            )

        if action == "verify":
            verify_form = MFALoginForm(request.POST)
            if verify_form.is_valid() and verify_mfa_code(user, verify_form.cleaned_data["code"]):
                user.mfa_enabled = True
                user.save(update_fields=["mfa_enabled"])
                log_action(user, "mfa_enabled", request, resource_id=str(user.id))
                messages.success(request, "Multi-factor authentication enabled.")
                return redirect("portal-mfa-settings")
            messages.error(request, "Unable to verify the authentication code.")

        if action == "disable":
            disable_form = MFADisableForm(request.POST)
            if not disable_form.is_valid():
                messages.error(request, "Enter your password and authentication code.")
            elif not user.check_password(disable_form.cleaned_data["password"]):
                messages.error(request, "Invalid password.")
            elif user.mfa_enabled and not verify_mfa_code(user, disable_form.cleaned_data["code"]):
                messages.error(request, "Invalid authentication code.")
            else:
                user.mfa_enabled = False
                user.mfa_secret = ""
                user.save(update_fields=["mfa_enabled", "mfa_secret"])
                log_action(user, "mfa_disabled", request, resource_id=str(user.id))
                messages.success(request, "Multi-factor authentication disabled.")
                return redirect("portal-mfa-settings")

    return render(
        request,
        "portal/security_mfa.html",
        {
            "provisioning_uri": provisioning_uri,
            "verify_form": verify_form,
            "disable_form": disable_form,
        },
    )


@login_required
def dashboard(request: HttpRequest):
    user = request.user

    if user.role == User.Role.PATIENT:
        patient = getattr(user, "patient_profile", None)
        if not patient:
            return _render_account_issue(
                request,
                "Patient",
                (
                    "Your patient profile has not been provisioned yet. "
                    "Please contact support or an administrator before booking care."
                ),
            )
        appointments = Appointment.objects.filter(patient=patient).order_by("-scheduled_time")
        records = (
            MedicalRecord.objects.filter(patient=patient)
            .prefetch_related("diagnoses", "prescriptions")
            .order_by("-created_at")
        )
        reports = Report.objects.filter(
            medical_record__patient=patient,
            status=Report.Status.APPROVED,
        ).order_by("-created_at")
        images = MedicalImage.objects.filter(patient=patient).order_by("-uploaded_at")
        for image in images:
            image.ai_result = get_ai_result_by_image(str(image.id)) or {}
            result_payload = image.ai_result.get("result", {})
            image.ai_probability = result_payload.get("anomaly_probability")
            image.ai_probability_available = image.ai_probability is not None
            image.ai_model = result_payload.get("model", "")
        context = {
            "appointments": appointments,
            "records": records,
            "reports": reports,
            "images": images,
            "appointment_form": AppointmentCreateForm(),
            "appointment_cancel_form": AppointmentCancelForm(),
            "image_form": ImageUploadForm(),
        }
        return _render_dashboard(request, "portal/dashboard_patient.html", context)

    if user.role == User.Role.DOCTOR:
        doctor = getattr(user, "doctor_profile", None)
        if not doctor:
            return _render_account_issue(
                request,
                "Doctor",
                (
                    "Your clinician profile is incomplete. Please contact an administrator "
                    "to finish provisioning before managing patients."
                ),
            )
        appointments = Appointment.objects.filter(doctor=doctor).order_by("-scheduled_time")
        records = (
            MedicalRecord.objects.filter(doctor=doctor)
            .prefetch_related("diagnoses", "prescriptions")
            .order_by("-created_at")
        )
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
            "diagnosis_form": DiagnosisCreateForm(user=user),
            "prescription_form": PrescriptionCreateForm(user=user),
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

    if user.role == User.Role.NURSE:
        context = {
            "today": timezone.localdate(),
        }
        return _render_dashboard(request, "portal/dashboard_nurse.html", context)

    action_filter = request.GET.get("action", "").strip()
    email_filter = request.GET.get("email", "").strip()
    resource_filter = request.GET.get("resource_id", "").strip()
    recent_audit_logs = AuditLog.objects.select_related("user").all()
    if action_filter:
        recent_audit_logs = recent_audit_logs.filter(action__icontains=action_filter)
    if email_filter:
        recent_audit_logs = recent_audit_logs.filter(user__email__icontains=email_filter)
    if resource_filter:
        recent_audit_logs = recent_audit_logs.filter(resource_id=resource_filter)

    context = {
        "user_count": User.objects.count(),
        "appointments": Appointment.objects.count(),
        "records": MedicalRecord.objects.count(),
        "reports": Report.objects.count(),
        "images": MedicalImage.objects.count(),
        "recent_audit_logs": recent_audit_logs[:50],
        "audit_filters": {
            "action": action_filter,
            "email": email_filter,
            "resource_id": resource_filter,
        },
    }
    return _render_dashboard(request, "portal/dashboard_admin.html", context)


@login_required
@require_POST
def book_appointment(request: HttpRequest):
    if request.user.role != User.Role.PATIENT:
        messages.error(request, "Not authorized")
        return redirect("portal-dashboard")

    if not getattr(request.user, "patient_profile", None):
        messages.error(request, "Your patient profile is not available yet.")
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
        _flash_form_errors(request, form, "Unable to create appointment.")
    return redirect("portal-dashboard")


@login_required
@require_POST
def upload_image(request: HttpRequest):
    if request.user.role != User.Role.PATIENT:
        messages.error(request, "Not authorized")
        return redirect("portal-dashboard")

    if not getattr(request.user, "patient_profile", None):
        messages.error(request, "Your patient profile is not available yet.")
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
            messages.success(
                request,
                "Image uploaded. AI processing will continue in the background if applicable.",
            )
    else:
        _flash_form_errors(request, form, "Invalid upload.")
    return redirect("portal-dashboard")


@login_required
def download_image(request: HttpRequest, image_id: str):
    image = get_authorized_image_for_user(request.user, image_id)
    if not image:
        messages.error(request, "Image not found")
        return redirect("portal-dashboard")

    storage = S3StorageService()
    log_action(request.user, "image_download", request, resource_id=str(image.id))

    if storage.use_s3:
        return HttpResponseRedirect(storage.presigned_url(image.s3_key))

    return FileResponse(
        storage.open_file(image.s3_key),
        content_type=image.content_type,
        as_attachment=True,
        filename=image.file_name,
    )


@login_required
@require_POST
def update_appointment_status(request: HttpRequest, appointment_id: str):
    if request.user.role != User.Role.DOCTOR:
        messages.error(request, "Not authorized")
        return redirect("portal-dashboard")

    if not getattr(request.user, "doctor_profile", None):
        messages.error(request, "Your clinician profile is not available yet.")
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
        _flash_form_errors(request, form, "Unable to update appointment.")
    return redirect("portal-dashboard")


@login_required
@require_POST
def cancel_appointment(request: HttpRequest, appointment_id: str):
    if request.user.role != User.Role.PATIENT:
        messages.error(request, "Not authorized")
        return redirect("portal-dashboard")

    if not getattr(request.user, "patient_profile", None):
        messages.error(request, "Your patient profile is not available yet.")
        return redirect("portal-dashboard")

    appointment = Appointment.objects.filter(
        id=appointment_id,
        patient=request.user.patient_profile,
    ).first()
    if not appointment:
        messages.error(request, "Appointment not found")
        return redirect("portal-dashboard")
    if appointment.status in {
        Appointment.Status.CANCELLED,
        Appointment.Status.COMPLETED,
        Appointment.Status.REJECTED,
    }:
        messages.error(request, "Appointment can no longer be cancelled")
        return redirect("portal-dashboard")

    appointment.status = Appointment.Status.CANCELLED
    appointment.save(update_fields=["status", "updated_at"])
    log_action(request.user, "appointment_cancel", request, resource_id=str(appointment.id))
    send_email_notification.delay(
        appointment.doctor.user.email,
        "Appointment cancelled",
        (
            f"{request.user.email} cancelled the appointment scheduled "
            f"for {appointment.scheduled_time}."
        ),
    )
    messages.success(request, "Appointment cancelled")
    return redirect("portal-dashboard")


@login_required
@require_POST
def create_medical_record(request: HttpRequest):
    if request.user.role != User.Role.DOCTOR:
        messages.error(request, "Not authorized")
        return redirect("portal-dashboard")

    if not getattr(request.user, "doctor_profile", None):
        messages.error(request, "Your clinician profile is not available yet.")
        return redirect("portal-dashboard")

    form = MedicalRecordCreateForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)
        record.doctor = request.user.doctor_profile
        record.save()
        log_action(request.user, "record_create", request, resource_id=str(record.id))
        messages.success(request, "Medical record created")
    else:
        _flash_form_errors(request, form, "Unable to create medical record.")
    return redirect("portal-dashboard")


@login_required
@require_POST
def add_diagnosis(request: HttpRequest):
    if request.user.role != User.Role.DOCTOR:
        messages.error(request, "Not authorized")
        return redirect("portal-dashboard")

    if not getattr(request.user, "doctor_profile", None):
        messages.error(request, "Your clinician profile is not available yet.")
        return redirect("portal-dashboard")

    form = DiagnosisCreateForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        record = form.cleaned_data["medical_record"]
        diagnosis = record.diagnoses.create(text=form.cleaned_data["text"])
        log_action(request.user, "diagnosis_create", request, resource_id=str(diagnosis.id))
        messages.success(request, "Diagnosis added")
    else:
        _flash_form_errors(request, form, "Unable to add diagnosis.")
    return redirect("portal-dashboard")


@login_required
@require_POST
def add_prescription(request: HttpRequest):
    if request.user.role != User.Role.DOCTOR:
        messages.error(request, "Not authorized")
        return redirect("portal-dashboard")

    if not getattr(request.user, "doctor_profile", None):
        messages.error(request, "Your clinician profile is not available yet.")
        return redirect("portal-dashboard")

    form = PrescriptionCreateForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        record = form.cleaned_data["medical_record"]
        prescription = record.prescriptions.create(
            medication_name=form.cleaned_data["medication_name"],
            dosage=form.cleaned_data["dosage"],
            instructions=form.cleaned_data.get("instructions", ""),
        )
        log_action(request.user, "prescription_create", request, resource_id=str(prescription.id))
        messages.success(request, "Prescription added")
    else:
        _flash_form_errors(request, form, "Unable to add prescription.")
    return redirect("portal-dashboard")


@login_required
@require_POST
def create_report(request: HttpRequest):
    if request.user.role != User.Role.DOCTOR:
        messages.error(request, "Not authorized")
        return redirect("portal-dashboard")

    if not getattr(request.user, "doctor_profile", None):
        messages.error(request, "Your clinician profile is not available yet.")
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
        _flash_form_errors(request, form, "Unable to create report.")
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


@login_required
def download_report(request: HttpRequest, report_id: str):
    report = (
        Report.objects.select_related(
            "author",
            "medical_record__patient__user",
            "medical_record__doctor__user",
        )
        .filter(id=report_id)
        .first()
    )
    if not report:
        messages.error(request, "Report not found")
        return redirect("portal-dashboard")

    if request.user.role == User.Role.PATIENT:
        if (
            report.medical_record.patient.user != request.user
            or report.status != Report.Status.APPROVED
        ):
            messages.error(request, "Not authorized")
            return redirect("portal-dashboard")
    elif request.user.role == User.Role.DOCTOR:
        if report.author != request.user:
            messages.error(request, "Not authorized")
            return redirect("portal-dashboard")
    elif request.user.role == User.Role.ADMIN:
        messages.error(request, "Administrators cannot download private patient reports.")
        return redirect("portal-dashboard")
    elif request.user.role not in {User.Role.RADIOLOGIST}:
        messages.error(request, "Not authorized")
        return redirect("portal-dashboard")

    author = report.author.email if report.author else "Unknown"
    body = "\n".join(
        [
            f"CuraMind AI Report ID: {report.id}",
            f"Status: {report.status}",
            f"Author: {author}",
            f"Patient: {report.medical_record.patient.user.email}",
            f"Doctor: {report.medical_record.doctor.user.email}",
            f"Created At: {report.created_at.isoformat()}",
            f"Approved At: {report.approved_at.isoformat() if report.approved_at else 'Pending'}",
            "",
            "Report Content",
            "==============",
            report.content,
            "",
        ]
    )
    response = HttpResponse(body, content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="curamind-report-{report.id}.txt"'
    log_action(request.user, "report_download", request, resource_id=str(report.id))
    return response
