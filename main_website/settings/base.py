import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

LOGIN_REDIRECT_URL = '/home/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

SECRET_KEY = os.environ.get('SECRET_KEY', 'changeme')




REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
    ),
}

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'app.accounts',
    'app.matrix',
    'widget_tweaks',
    'channels',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
]

ROOT_URLCONF = 'main_website.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'main_website.wsgi.application'
ASGI_APPLICATION = 'main_website.asgi.application'
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.environ.get("POSTGRES_DB", 'qc_matrix'),
        'USER': os.environ.get("POSTGRES_USER", 'qc_admin'),
        'PASSWORD': os.environ.get("POSTGRES_PASSWORD", 'qc_admin_pass'),
        'HOST': os.environ.get("POSTGRES_HOST", 'db'),
        'PORT': os.environ.get("POSTGRES_PORT", '5432'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/Mexico_City'

USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = '/vol/static'
MEDIA_ROOT = '/vol/media'
MEDIA_URL = '/media/'

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

EXCEL_DIR = os.path.join(BASE_DIR, 'static', 'excel_files')
DATA_UPLOAD_MAX_NUMBER_FIELDS = 5000

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'accounts.User'

USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'http')


CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            # El host 'redis' es el nombre del servicio en Docker Compose
            "hosts": [(os.environ.get('REDIS_HOST', 'redis'), 6379)],
        },
    },
}

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# Al final de tu settings.py de producción
# Al final de tu settings.py de producción
SECURE_CROSS_ORIGIN_OPENER_POLICY = None

# Configuración correcta de X-Frame-Options
X_FRAME_OPTIONS = 'SAMEORIGIN'

# Otros headers de seguridad (opcional)
SECURE_BROWSER_XSS_FILTER = False
SECURE_CONTENT_TYPE_NOSNIFF = False
SECURE_HSTS = False
SECURE_HSTS_PRELOAD = False
SECURE_HSTS_INCLUDE_SUBDOMAINS = False