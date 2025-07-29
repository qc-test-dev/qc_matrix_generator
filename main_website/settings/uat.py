import os
from .base import *

ALLOWED_HOSTS = ['200.57.172.7', 'tu-dominio.com', 'app', 'localhost', '127.0.0.1']

# CSRF para WebSockets
CSRF_TRUSTED_ORIGINS = [
    'http://200.57.172.7:8080',    # ← Agregar con puerto 8080
    'http://200.57.172.7',         # Mantener sin puerto por si acaso
    'ws://200.57.172.7:8080',      # Para WebSockets con puerto
    'ws://200.57.172.7',           # Para WebSockets sin puerto
    'http://localhost:8080',       # Para desarrollo local
    'http://localhost',
    'http://127.0.0.1:8080',       # Para desarrollo local
    'http://127.0.0.1',
    'ws://localhost:8080',
    'ws://localhost',
    'ws://127.0.0.1:8080',
    'ws://127.0.0.1',
    'ws://app',
]

DEBUG = True

SESSION_COOKIE_NAME = 'uat_sessionid'
CSRF_COOKIE_NAME = 'uat_csrftoken'

# ⚡ AGREGAR ESTA CONFIGURACIÓN PARA CHANNELS
REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')  # 'redis' si usas docker-compose
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(REDIS_HOST, 6379)],
        },
    }
}

# También asegúrate de tener esto
ASGI_APPLICATION = 'main_website.asgi.application'