#!/bin/bash
set -e

echo "🚀 Starting Django application setup..."

# Configurar directorios
echo "🔧 Creating necessary directories..."
mkdir -p /vol/static/excel_files /vol/static/admin /vol/static/css /vol/static/js /vol/web/media
chmod -R 755 /vol/static
chmod -R 755 /vol/web/media

# Configurar socket
echo "🔧 Setting up socket directory..."
mkdir -p /tmp/sockets
chmod -R 770 /tmp/sockets
chown -R 1000:1000 /tmp/sockets

# Migraciones
echo "🔄 Running database migrations..."
python manage.py makemigrations --noinput
python manage.py migrate --noinput

# Cargar datos iniciales (si existe el fixture)
if [ -f "initialdata.json" ]; then
    echo "📂 Loading initial data..."
    python manage.py loaddata initialdata.json
fi

# Archivos estáticos
echo "📦 Collecting static files..."
python manage.py collectstatic --noinput --clear

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
exec uwsgi --socket /tmp/sockets/uwsgi.sock \
     --module main_website.wsgi \
     --master \
     --processes 4 \
     --threads 2 \
     --chmod-socket=660 \
     --uid 1000 \
     --gid 1000 \
     --enable-threads