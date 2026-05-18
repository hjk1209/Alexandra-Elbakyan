from .base import *  # noqa: F401,F403

DEBUG = True
USE_LOCAL_STATE = True

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': '',
        'OPTIONS': {},
    }
}

SESSION_ENGINE = 'django.contrib.sessions.backends.db'
