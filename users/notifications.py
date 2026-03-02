import logging

from django.conf import settings
from django.core.mail import send_mail


logger = logging.getLogger(__name__)


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
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [patient_email],
            fail_silently=False,
        )
        return True
    except Exception:
        logger.exception(
            "Failed to send appointment status email for appointment_id=%s",
            appointment.id,
        )
        return False
