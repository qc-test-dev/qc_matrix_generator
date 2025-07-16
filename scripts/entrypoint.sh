#!/bin/bash
set -e

echo "🚀 Starting Django application setup..."

# 1) Superusuario (igual que antes)
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

# 2) Migraciones & static
echo "🗄️  Applying migrations and collecting static files..."
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput --clear

# 3) Iniciar Daphne (ASGI) para HTTP + WebSocket
echo "🚀 Starting Daphne ASGI server on port 8000..."
exec daphne -b 0.0.0.0 -p 8000 main_website.asgi:application
