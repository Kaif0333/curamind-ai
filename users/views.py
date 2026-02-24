from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, HttpResponseForbidden
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.conf import settings
from django.views.decorators.http import require_POST
from .models import Appointment, User


def _require_user_type(user, expected_type):
    return user.is_authenticated and user.user_type == expected_type


@login_required
def role_redirect(request):
    if request.user.is_staff or request.user.is_superuser:
        return redirect('/admin/')
    if request.user.user_type == 'doctor':
        return redirect('doctor_dashboard')
    elif request.user.user_type == 'patient':
        return redirect('patient_dashboard')
    return HttpResponse("Invalid role")


# ---------------- PATIENT ----------------

@login_required
def patient_dashboard(request):
    if not _require_user_type(request.user, 'patient'):
        return HttpResponseForbidden("Only patients can access this page.")

    appointments = Appointment.objects.filter(patient=request.user).order_by('-date', '-time')
    return render(request, 'users/patient_dashboard.html', {
        'appointments': appointments
    })


@login_required
def book_appointment(request):
    if not _require_user_type(request.user, 'patient'):
        return HttpResponseForbidden("Only patients can book appointments.")

    doctors = User.objects.filter(user_type='doctor')
    if request.method == "POST":
        doctor_id = request.POST.get('doctor')
        date = request.POST.get('date')
        time = request.POST.get('time')
        description = request.POST.get('description')
        doctor = get_object_or_404(User, id=doctor_id, user_type='doctor')

        try:
            Appointment.objects.create(
                patient=request.user,
                doctor=doctor,
                date=date,
                time=time,
                description=description,
                status='pending'
            )
        except ValidationError as exc:
            booking_error = "; ".join(
                [message for messages in exc.message_dict.values() for message in messages]
            )
            messages.error(request, booking_error)
        else:
            return redirect('patient_dashboard')

    return render(request, 'users/book_appointment.html', {
        'doctors': doctors,
    })


# ---------------- DOCTOR ----------------

@login_required
def doctor_dashboard(request):
    if not _require_user_type(request.user, 'doctor'):
        return HttpResponseForbidden("Only doctors can access this page.")

    appointments = Appointment.objects.filter(doctor=request.user).order_by('-date', '-time')
    return render(request, 'users/doctor_dashboard.html', {
        'appointments': appointments
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

    send_mail(
        'Appointment Approved',
        f'Your appointment on {appointment.date} is approved.',
        settings.DEFAULT_FROM_EMAIL,
        [appointment.patient.email],
        fail_silently=True
    )

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

    send_mail(
        'Appointment Rejected',
        'Your appointment was rejected.',
        settings.DEFAULT_FROM_EMAIL,
        [appointment.patient.email],
        fail_silently=True
    )

    return redirect('doctor_dashboard')
