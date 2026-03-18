import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


@shared_task
def send_email_notification(to_email: str, subject: str, message: str) -> None:
    if not to_email:
        logger.info("No recipient for email notification")
        return
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [to_email],
            fail_silently=True,
        )
    except Exception as exc:
        logger.exception("Failed to send email notification: %s", exc)
