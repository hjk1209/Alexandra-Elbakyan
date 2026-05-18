from .base import *  # noqa: F401,F403

if SECRET_KEY == "dev-only-change-me-before-production":
    raise ImproperlyConfigured('Defina RAIZ_SECRET_KEY com um valor forte antes de subir em producao.')
