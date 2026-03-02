from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.http import HttpResponse, HttpResponseForbidden
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.utils import timezone
from .models import Appointment
from .forms import AppointmentBookingForm, PatientRegistrationForm, DoctorRegistrationForm
from .notifications import send_appointment_status_email


def _require_user_type(user, expected_type):
    return user.is_authenticated and user.user_type == expected_type


def register_patient(request):
    return _register_user(
        request,
        form_class=PatientRegistrationForm,
        template_name='registration/register.html',
        role_label='Patient',
        redirect_name='patient_dashboard',
    )


def register_doctor(request):
    return _register_user(
        request,
        form_class=DoctorRegistrationForm,
        template_name='registration/register.html',
        role_label='Doctor',
        redirect_name='doctor_dashboard',
    )


def _register_user(request, form_class, template_name, role_label, redirect_name):
    if request.user.is_authenticated:
        return redirect('role_redirect')

    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect(redirect_name)
        form_errors = []
        for _, errors in form.errors.items():
            form_errors.extend(errors)
        messages.error(request, "; ".join(form_errors) or "Please fix the form errors.")
    else:
        form = form_class()

    return render(request, template_name, {'form': form, 'role_label': role_label})


@login_required
def role_redirect(request):
    if request.user.is_superuser:
        return redirect('/admin/')
    if request.user.user_type == 'doctor':
        return redirect('doctor_dashboard')
    elif request.user.user_type == 'patient':
        return redirect('patient_dashboard')
    if request.user.is_staff:
        return redirect('/admin/')
    return HttpResponse("Invalid role")


# ---------------- PATIENT ----------------

@login_required
def patient_dashboard(request):
    if not _require_user_type(request.user, 'patient'):
        return HttpResponseForbidden("Only patients can access this page.")

    appointments = Appointment.objects.filter(patient=request.user)
    status_filter = request.GET.get('status', '').strip()
    query = request.GET.get('q', '').strip()
    date_filter = request.GET.get('date', '').strip()

    if status_filter in ['pending', 'approved', 'rejected']:
        appointments = appointments.filter(status=status_filter)
    if query:
        appointments = appointments.filter(Q(doctor__username__icontains=query) | Q(description__icontains=query))
    if date_filter:
        appointments = appointments.filter(date=date_filter)

    appointments = appointments.order_by('-date', '-time')
    return render(request, 'users/patient_dashboard.html', {
        'appointments': appointments,
        'status_filter': status_filter,
        'query': query,
        'date_filter': date_filter,
    })


@login_required
def book_appointment(request):
    if not _require_user_type(request.user, 'patient'):
        return HttpResponseForbidden("Only patients can book appointments.")

    if request.method == "POST":
        form = AppointmentBookingForm(request.POST)
        if form.is_valid():
            form.save(patient=request.user)
            return redirect('patient_dashboard')
        form_errors = []
        for _, errors in form.errors.items():
            form_errors.extend(errors)
        messages.error(request, "; ".join(form_errors) or "Please fix the form errors.")
    else:
        form = AppointmentBookingForm()

    return render(request, 'users/book_appointment.html', {
        'form': form,
    })


# ---------------- DOCTOR ----------------

@login_required
def doctor_dashboard(request):
    if not _require_user_type(request.user, 'doctor'):
        return HttpResponseForbidden("Only doctors can access this page.")

    appointments = Appointment.objects.filter(doctor=request.user)
    status_filter = request.GET.get('status', '').strip()
    query = request.GET.get('q', '').strip()
    date_filter = request.GET.get('date', '').strip()

    if status_filter in ['pending', 'approved', 'rejected']:
        appointments = appointments.filter(status=status_filter)
    if query:
        appointments = appointments.filter(Q(patient__username__icontains=query) | Q(description__icontains=query))
    if date_filter:
        appointments = appointments.filter(date=date_filter)

    appointments = appointments.order_by('-date', '-time')
    today = timezone.localdate()
    today_counts = list(Appointment.objects.filter(doctor=request.user, date=today).values_list('status', flat=True))
    summary = {
        'today_total': len(today_counts),
        'today_pending': today_counts.count('pending'),
        'today_approved': today_counts.count('approved'),
        'today_rejected': today_counts.count('rejected'),
    }
    return render(request, 'users/doctor_dashboard.html', {
        'appointments': appointments,
        'status_filter': status_filter,
        'query': query,
        'date_filter': date_filter,
        'summary': summary,
        'today': today,
    })


@login_required
@require_POST
def approve_appointment(request, appointment_id):
    if not _require_user_type(request.user, 'doctor'):
        return HttpResponseForbidden("Only doctors can approve appointments.")

    appointment = get_object_or_404(Appointment, id=appointment_id, doctor=request.user)
    if appointment.status != 'pending':
        return redirect('doctor_dashboard')

    appointment.status = 'approved'
    try:
        appointment.save()
    except ValidationError as exc:
        messages.error(request, "; ".join(
            [message for error_list in exc.message_dict.values() for message in error_list]
        ))
        return redirect('doctor_dashboard')

    if not send_appointment_status_email(appointment):
        messages.warning(request, "Appointment approved, but confirmation email could not be sent.")

    return redirect('doctor_dashboard')


@login_required
@require_POST
def reject_appointment(request, appointment_id):
    if not _require_user_type(request.user, 'doctor'):
        return HttpResponseForbidden("Only doctors can reject appointments.")

    appointment = get_object_or_404(Appointment, id=appointment_id, doctor=request.user)
    if appointment.status != 'pending':
        return redirect('doctor_dashboard')

    appointment.status = 'rejected'
    try:
        appointment.save()
    except ValidationError as exc:
        messages.error(request, "; ".join(
            [message for error_list in exc.message_dict.values() for message in error_list]
        ))
        return redirect('doctor_dashboard')

    if not send_appointment_status_email(appointment):
        messages.warning(request, "Appointment rejected, but confirmation email could not be sent.")

    return redirect('doctor_dashboard')
