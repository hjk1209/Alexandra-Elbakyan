import os
import sys
from importlib.util import find_spec
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def load_env_file(path):
    if not path.exists():
        return
    for raw_line in path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        name, value = line.split('=', 1)
        os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))


load_env_file(BASE_DIR / '.env')


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    raw_value = os.environ.get(name, default)
    return [item.strip() for item in raw_value.split(",") if item.strip()]


HAS_DAPHNE = find_spec('daphne') is not None
HAS_CHANNELS = find_spec('channels') is not None
HAS_WHITENOISE = find_spec('whitenoise') is not None

SECRET_KEY = os.environ.get("RAIZ_SECRET_KEY", "dev-only-change-me-before-production")
DEBUG = env_bool("RAIZ_DEBUG", False)
IS_TEST = 'test' in sys.argv
IS_MANAGE_COMMAND = Path(sys.argv[0]).name.lower() == 'manage.py'
USE_LOCAL_STATE = DEBUG or IS_TEST
ALLOWED_HOSTS = env_list("RAIZ_ALLOWED_HOSTS", "127.0.0.1,localhost,testserver")
CSRF_TRUSTED_ORIGINS = env_list("RAIZ_CSRF_TRUSTED_ORIGINS")
RAIZ_ENABLE_REALTIME = env_bool("RAIZ_ENABLE_REALTIME", HAS_DAPHNE and HAS_CHANNELS)

if (
    not DEBUG
    and SECRET_KEY == "dev-only-change-me-before-production"
    and not (IS_TEST or IS_MANAGE_COMMAND)
):
    raise ImproperlyConfigured('Defina RAIZ_SECRET_KEY com um valor forte antes de subir em producao.')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
    'accounts',
    'social',
    'messaging',
    'health',
]

if RAIZ_ENABLE_REALTIME:
    INSTALLED_APPS.insert(0, 'daphne')
    INSTALLED_APPS.append('channels')

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'core.middleware.SecurityHeadersMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

if HAS_WHITENOISE:
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

ROOT_URLCONF = 'juventude_mst.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'juventude_mst.wsgi.application'
ASGI_APPLICATION = 'juventude_mst.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': os.environ.get('RAIZ_DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.environ.get('RAIZ_DB_NAME', str(BASE_DIR / 'db.sqlite3')),
        'USER': os.environ.get('RAIZ_DB_USER', ''),
        'PASSWORD': os.environ.get('RAIZ_DB_PASSWORD', ''),
        'HOST': os.environ.get('RAIZ_DB_HOST', ''),
        'PORT': os.environ.get('RAIZ_DB_PORT', ''),
        'ATOMIC_REQUESTS': not USE_LOCAL_STATE,
        'CONN_MAX_AGE': 600,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 12},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]
try:
    import argon2  # noqa: F401
except ImportError:
    try:
        import bcrypt  # noqa: F401
    except ImportError:
        pass
    else:
        PASSWORD_HASHERS.insert(0, 'django.contrib.auth.hashers.BCryptSHA256PasswordHasher')
else:
    PASSWORD_HASHERS.insert(0, 'django.contrib.auth.hashers.Argon2PasswordHasher')

AUTH_USER_MODEL = 'accounts.User'

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': (
            'whitenoise.storage.CompressedManifestStaticFilesStorage'
            if HAS_WHITENOISE
            else 'django.contrib.staticfiles.storage.StaticFilesStorage'
        ),
    },
}

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'feed'
LOGOUT_REDIRECT_URL = 'home'

EMAIL_BACKEND = os.environ.get(
    'RAIZ_EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend' if USE_LOCAL_STATE else 'django.core.mail.backends.smtp.EmailBackend'
)
EMAIL_HOST = os.environ.get('RAIZ_EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.environ.get('RAIZ_EMAIL_PORT', '587'))
EMAIL_USE_TLS = env_bool('RAIZ_EMAIL_USE_TLS', not USE_LOCAL_STATE)
EMAIL_HOST_USER = os.environ.get('RAIZ_EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('RAIZ_EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('RAIZ_DEFAULT_FROM_EMAIL', 'no-reply@raizcoletiva.local')
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

(BASE_DIR / 'logs').mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'raiz.log',
            'maxBytes': 1024 * 1024 * 10,
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'security_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'security.log',
            'maxBytes': 1024 * 1024 * 10,
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'raiz.security': {
            'handlers': ['console', 'security_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

if RAIZ_ENABLE_REALTIME:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': os.environ.get(
                'RAIZ_CHANNEL_BACKEND',
                'channels.layers.InMemoryChannelLayer' if USE_LOCAL_STATE else 'channels_redis.core.RedisChannelLayer'
            ),
            'CONFIG': {
                'hosts': [os.environ.get('RAIZ_REDIS_URL', 'redis://127.0.0.1:6379/1')] if not USE_LOCAL_STATE else [],
            }
        }
    }

ELASTICSEARCH_DSL = {
    'default': {
        'hosts': os.environ.get('RAIZ_ELASTICSEARCH_HOSTS', 'localhost:9200'),
        'http_auth': (
            os.environ.get('RAIZ_ELASTICSEARCH_USER', ''),
            os.environ.get('RAIZ_ELASTICSEARCH_PASSWORD', '')
        ) if not USE_LOCAL_STATE else None,
        'verify_certs': env_bool('RAIZ_ELASTICSEARCH_VERIFY_CERTS', False),
    },
}

GRAFANA_URL = os.environ.get('RAIZ_GRAFANA_URL', 'http://localhost:3000')
GRAFANA_API_KEY = os.environ.get('RAIZ_GRAFANA_API_KEY', '')
PROMETHEUS_EXPORT_MIGRATIONS = True

FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 4 * 1024 * 1024

CACHES = {
    'default': {
        'BACKEND': os.environ.get(
            'RAIZ_CACHE_BACKEND',
            'django.core.cache.backends.locmem.LocMemCache'
            if USE_LOCAL_STATE
            else 'django.core.cache.backends.redis.RedisCache'
        ),
        'LOCATION': os.environ.get('RAIZ_CACHE_LOCATION', '' if USE_LOCAL_STATE else 'redis://127.0.0.1:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_CLASS_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            }
        } if not USE_LOCAL_STATE else {}
    }
}

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

SESSION_COOKIE_AGE = 60 * 60 * 8
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = not USE_LOCAL_STATE
SESSION_COOKIE_NAME = 'raiz_sessionid'
SESSION_ENGINE = 'django.contrib.sessions.backends.db' if USE_LOCAL_STATE else 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = not USE_LOCAL_STATE
CSRF_COOKIE_NAME = 'raiz_csrftoken'

SECURE_SSL_REDIRECT = env_bool('RAIZ_SECURE_SSL_REDIRECT', False if USE_LOCAL_STATE else True)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = 0 if USE_LOCAL_STATE else 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = not USE_LOCAL_STATE
SECURE_HSTS_PRELOAD = not USE_LOCAL_STATE
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
SECURE_CROSS_ORIGIN_RESOURCE_POLICY = 'same-origin'
RAIZ_TRUST_X_FORWARDED_FOR = env_bool('RAIZ_TRUST_X_FORWARDED_FOR', False)
USE_X_FORWARDED_HOST = env_bool('RAIZ_USE_X_FORWARDED_HOST', False)
X_FRAME_OPTIONS = 'DENY'

MAX_LOGIN_FAILURES = int(os.environ.get('RAIZ_MAX_LOGIN_FAILURES', '5'))
LOGIN_LOCK_WINDOW_MINUTES = int(os.environ.get('RAIZ_LOGIN_LOCK_WINDOW_MINUTES', '15'))
POST_RATE_LIMIT_PER_MINUTE = int(os.environ.get('RAIZ_POST_RATE_LIMIT_PER_MINUTE', '8'))
COMMENT_RATE_LIMIT_PER_MINUTE = int(os.environ.get('RAIZ_COMMENT_RATE_LIMIT_PER_MINUTE', '25'))
MESSAGE_RATE_LIMIT_PER_MINUTE = int(os.environ.get('RAIZ_MESSAGE_RATE_LIMIT_PER_MINUTE', '40'))
SIGNUP_RATE_LIMIT_PER_HOUR = int(os.environ.get('RAIZ_SIGNUP_RATE_LIMIT_PER_HOUR', '10'))
RECOVERY_RATE_LIMIT_PER_HOUR = int(os.environ.get('RAIZ_RECOVERY_RATE_LIMIT_PER_HOUR', '6'))
LIKE_RATE_LIMIT_PER_MINUTE = int(os.environ.get('RAIZ_LIKE_RATE_LIMIT_PER_MINUTE', '80'))
REPORT_RATE_LIMIT_PER_MINUTE = int(os.environ.get('RAIZ_REPORT_RATE_LIMIT_PER_MINUTE', '15'))
UPLOAD_RATE_LIMIT_PER_MINUTE = int(os.environ.get('RAIZ_UPLOAD_RATE_LIMIT_PER_MINUTE', '12'))
LOGIN_API_RATE_LIMIT_PER_MINUTE = int(os.environ.get('RAIZ_LOGIN_API_RATE_LIMIT_PER_MINUTE', '12'))
TWO_FACTOR_CODE_TTL_MINUTES = int(os.environ.get('RAIZ_TWO_FACTOR_CODE_TTL_MINUTES', '10'))
JWT_ACCESS_TOKEN_TTL_MINUTES = int(os.environ.get('RAIZ_JWT_ACCESS_TOKEN_TTL_MINUTES', '10'))
JWT_REFRESH_TOKEN_TTL_DAYS = int(os.environ.get('RAIZ_JWT_REFRESH_TOKEN_TTL_DAYS', '7'))
JWT_REFRESH_COOKIE_NAME = os.environ.get('RAIZ_JWT_REFRESH_COOKIE_NAME', 'raiz_refresh_token')
JWT_ISSUER = os.environ.get('RAIZ_JWT_ISSUER', 'raiz-coletiva')
JWT_AUDIENCE = os.environ.get('RAIZ_JWT_AUDIENCE', 'raiz-coletiva-api')
PROTECTED_MEDIA_TOKEN_TTL_SECONDS = int(os.environ.get('RAIZ_PROTECTED_MEDIA_TOKEN_TTL_SECONDS', '900'))
RAIZ_BLOCKED_TERMS = env_list('RAIZ_BLOCKED_TERMS')
RAIZ_SENSITIVE_TERMS = env_list('RAIZ_SENSITIVE_TERMS')
