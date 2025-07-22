"""
WSGI config for main_website project.
"""

import os
from django.core.wsgi import get_wsgi_application

# 🎯 Usar variable de entorno para settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 
    os.environ.get('DJANGO_SETTINGS_MODULE', 'main_website.settings.prod'))

application = get_wsgi_application()