#!/bin/bash

echo "🚀 Starting Django application..."

# Fix volume permissions
echo "🔧 Fixing volume permissions..."
sudo chown -R qc-lab:qc-lab /vol/static 2>/dev/null || true
sudo chown -R qc-lab:qc-lab /vol/web/media 2>/dev/null || true
mkdir -p /vol/static/excel_files
mkdir -p /vol/static/admin
mkdir -p /vol/static/css
mkdir -p /vol/static/js
chmod -R 755 /vol/static
chmod -R 755 /vol/web/media

echo "✅ Database permissions fixed"

echo "📝 Making migrations..."
python manage.py makemigrations --noinput

echo "🔄 Applying migrations..."
python manage.py migrate --noinput

echo "📊 Loading initial data..."
python manage.py loaddata initial_data.json

echo "👤 Creating superuser if needed..."
python manage.py shell << EOF
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
EOF

echo "Running migrations..."
python manage.py migrate

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "🚀 Starting uWSGI server..."
uwsgi --socket :8000 --module main_website.wsgi --master --processes 4 --threads 2