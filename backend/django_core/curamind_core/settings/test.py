"""Test settings."""

from .base import *  # noqa: F401,F403
from .base import REST_FRAMEWORK as BASE_REST_FRAMEWORK

DEBUG = True
SECRET_KEY = "test-secret-key-that-is-definitely-long-enough-for-jwt-usage"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

REST_FRAMEWORK = BASE_REST_FRAMEWORK.copy()
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
