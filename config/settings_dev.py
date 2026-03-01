from .settings import *  # noqa: F401,F403

# Development-first defaults.
DEBUG = True
ALLOWED_HOSTS = ALLOWED_HOSTS or ['127.0.0.1', 'localhost', 'testserver']

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
