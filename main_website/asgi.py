import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import app.matrix.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 
    os.environ.get('DJANGO_SETTINGS_MODULE', 'main_website.settings.prod'))

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            app.matrix.routing.websocket_urlpatterns
        )
    ),
})