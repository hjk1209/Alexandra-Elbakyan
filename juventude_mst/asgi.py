"""
ASGI config for juventude_mst project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'juventude_mst.settings')

django_asgi_app = get_asgi_application()
application = django_asgi_app

try:
    from channels.auth import AuthMiddlewareStack
    from channels.routing import ProtocolTypeRouter, URLRouter
    from channels.security.websocket import AllowedHostsOriginValidator
except ImportError:
    application = django_asgi_app
else:
    from core.routing import websocket_urlpatterns

    application = ProtocolTypeRouter(
        {
            'http': django_asgi_app,
            'websocket': AllowedHostsOriginValidator(
                AuthMiddlewareStack(
                    URLRouter(websocket_urlpatterns)
                )
            ),
        }
    )

