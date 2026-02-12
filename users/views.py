from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.core.mail import send_mail
from django.conf import settings
from .models import Appointment, User


@login_required
def role_redirect(request):
    if request.user.user_type == 'doctor':
        return redirect('doctor_dashboard')
    elif request.user.user_type == 'patient':
        return redirect('patient_dashboard')
    return HttpResponse("Invalid role")


# ---------------- PATIENT ----------------

@login_required
def patient_dashboard(request):
    appointments = Appointment.objects.filter(patient=request.user)
    return render(request, 'users/patient_dashboard.html', {
        'appointments': appointments
    })


@login_required
def book_appointment(request):
    doctors = User.objects.filter(user_type='doctor')

    if request.method == "POST":
        doctor_id = request.POST.get('doctor')
        date = request.POST.get('date')
        time = request.POST.get('time')
        description = request.POST.get('description')

        Appointment.objects.create(
            patient=request.user,
            doctor_id=doctor_id,
            date=date,
            time=time,
            description=description,
            status='pending'
        )

        return redirect('patient_dashboard')

    return render(request, 'users/book_appointment.html', {
        'doctors': doctors
    })


# ---------------- DOCTOR ----------------

@login_required
def doctor_dashboard(request):
    appointments = Appointment.objects.filter(doctor=request.user)
    return render(request, 'users/doctor_dashboard.html', {
        'appointments': appointments
    })


@login_required
def approve_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    appointment.status = 'approved'
    appointment.save()

    send_mail(
        'Appointment Approved',
        f'Your appointment on {appointment.date} is approved.',
        settings.DEFAULT_FROM_EMAIL,
        [appointment.patient.email],
        fail_silently=True
    )

    return redirect('doctor_dashboard')


@login_required
def reject_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    appointment.status = 'rejected'
    appointment.save()

    send_mail(
        'Appointment Rejected',
        'Your appointment was rejected.',
        settings.DEFAULT_FROM_EMAIL,
        [appointment.patient.email],
        fail_silently=False
    )

    return redirect('doctor_dashboard')
