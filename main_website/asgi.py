import os
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
import app.matrix.routing

# 👇 Aquí usa el mismo settings que usas con manage_local.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main_website.bk_settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            app.matrix.routing.websocket_urlpatterns
        )
    ),
})
