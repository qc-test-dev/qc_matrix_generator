from .base import *
import os

DEBUG = False

# Hosts permitidos
ALLOWED_HOSTS = [
    '200.57.172.7',
    'localhost',
    '127.0.0.1',
    '.tu-dominio.com',  # Permite subdominios
]

# CSRF para WebSockets
CSRF_TRUSTED_ORIGINS = [
    'http://200.57.172.7',
    'ws://200.57.172.7',  # ← IMPORTANTE para WebSockets
    'http://localhost',
    'http://127.0.0.1',
    'ws://localhost',
    'ws://127.0.0.1',
]

# Cookies seguras
SESSION_COOKIE_NAME = 'prod_sessionid'
CSRF_COOKIE_NAME = 'prod_csrftoken'
SESSION_COOKIE_SECURE = False  # True cuando uses HTTPS
CSRF_COOKIE_SECURE = False     # True cuando uses HTTPS
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False   # False para que JS pueda leerla

# Redis para Channels (asegúrate de que esté configurado)
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(REDIS_HOST, 6379)],
            "capacity": 1500,
            "expiry": 10,
        },
    },
}

# Configuración para WebSockets con proxy reverso
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Si usas Nginx, estas son importantes
X_FRAME_OPTIONS = 'SAMEORIGIN'
SECURE_CROSS_ORIGIN_OPENER_POLICY = None

# Timeouts para WebSockets
CHANNEL_LAYER_TTL = 86400  # 24 horas
ASGI_THREADS = 1000

# Cache (opcional pero recomendado)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'redis://{REDIS_HOST}:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Para debug en producción (quitar después)
if os.environ.get('DEBUG_WEBSOCKET'):
    LOGGING['loggers']['channels']['level'] = 'DEBUG'
    LOGGING['loggers']['daphne'] = {
        'handlers': ['console'],
        'level': 'DEBUG',
    }