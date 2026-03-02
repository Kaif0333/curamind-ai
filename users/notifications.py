import logging

from django.conf import settings
from django.core.mail import send_mail
import requests


logger = logging.getLogger(__name__)


def _send_via_smtp(subject, message, recipient):
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [recipient],
        fail_silently=False,
    )


def _send_via_resend(subject, message, recipient):
    api_key = getattr(settings, "RESEND_API_KEY", "")
    from_email = getattr(settings, "RESEND_FROM_EMAIL", "") or getattr(settings, "DEFAULT_FROM_EMAIL", "")
    if not api_key or not from_email:
        raise ValueError("RESEND_API_KEY and RESEND_FROM_EMAIL (or DEFAULT_FROM_EMAIL) are required.")

    response = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "from": from_email,
            "to": [recipient],
            "subject": subject,
            "text": message,
        },
        timeout=15,
    )
    response.raise_for_status()


def send_appointment_status_email(appointment):
    patient_email = (appointment.patient.email or "").strip()
    if not patient_email:
        return False

    status_label = appointment.status.capitalize()
    subject = f"Appointment {status_label}"
    message = (
        f"Hello {appointment.patient.username},\n\n"
        f"Your appointment with Dr. {appointment.doctor.username} on "
        f"{appointment.date} at {appointment.time} was {appointment.status}.\n\n"
        "Thank you,\nCuraMind AI"
    )

    try:
        provider = getattr(settings, "EMAIL_PROVIDER", "smtp").lower()
        if provider == "resend":
            _send_via_resend(subject, message, patient_email)
        else:
            _send_via_smtp(subject, message, patient_email)
        return True
    except Exception:
        logger.exception(
            "Failed to send appointment status email for appointment_id=%s",
            appointment.id,
        )
        return False
