import os
import os
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
import app.matrix.routing

# 🎯 Cambiar esta línea para usar la variable de entorno
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