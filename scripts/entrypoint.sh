
#!/bin/bash
set -e

echo "🚀 Starting Django application setup..."


# Superusuario
if [ "$DJANGO_SUPERUSER_USERNAME" ]; then
    echo "👤 Checking/creating superuser..."
    python manage.py shell -c "
import os
from django.contrib.auth import get_user_model
User = get_user_model()
username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
"
fi

# Iniciar uWSGI
echo "🚀 Starting uWSGI server..."
exec uwsgi --socket :8080 \
     --master \
     --module main_website.wsgi \
     --enable-threads