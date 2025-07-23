import os
from .base import *

ALLOWED_HOSTS = ['200.57.172.7', 'tu-dominio.com', 'app', 'localhost', '127.0.0.1']

# CSRF para WebSockets
CSRF_TRUSTED_ORIGINS = [
    'http://200.57.172.7',
    'ws://200.57.172.7',
    'http://localhost',
    'http://127.0.0.1',
    'ws://localhost',
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