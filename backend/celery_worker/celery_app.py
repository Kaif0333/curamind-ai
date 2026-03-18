import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "curamind_core.settings")

app = Celery("curamind")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
app.conf.broker_connection_retry_on_startup = True
