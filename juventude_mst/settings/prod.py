from .base import *  # noqa: F401,F403

WEAK_SECRET_KEYS = {
    '',
    'dev-only-change-me-before-production',
    'dev-local-change-me',
    'dev-compose-change-me-before-production',
    'troque-por-uma-chave-forte',
}

if (
    not SECRET_KEY
    or SECRET_KEY in WEAK_SECRET_KEYS
    or SECRET_KEY.startswith('troque-por-')
    or len(SECRET_KEY) < 32
):
    raise ImproperlyConfigured('Defina RAIZ_SECRET_KEY com um valor forte antes de subir em producao.')
