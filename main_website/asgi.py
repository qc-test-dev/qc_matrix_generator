import os
from django.core.asgi import get_asgi_application

# IMPORTANTE: Configurar settings ANTES de importar channels
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main_website.settings.prod')

# Inicializar Django ANTES de importar los routing
django_asgi_app = get_asgi_application()

# AHORA importar channels y routing
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
from app.matrix import routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                routing.websocket_urlpatterns
            )
        )
    ),
})