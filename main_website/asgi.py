# En main_website/asgi.py - cambiar a:
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 
    os.environ.get('DJANGO_SETTINGS_MODULE', 'main_website.settings.prod'))

application = get_asgi_application()