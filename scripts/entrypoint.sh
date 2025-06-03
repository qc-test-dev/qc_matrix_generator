#!/bin/sh
set -e
echo "🚀 Starting Django application..."
sleep 2
mkdir -p /app/db/

# Asegurar permisos correctos de la base de datos
if [ -f db.sqlite3 ]; then
    chmod 664 db.sqlite3
    echo "✅ Database permissions fixed"
fi

# Generar migraciones
echo "📝 Making migrations..."
python manage.py makemigrations

# Aplicar migraciones
echo "🔄 Applying migrations..."
python manage.py migrate

# Cargar datos iniciales (solo si existe el archivo)
if [ -f initial_data.json ]; then
    echo "📊 Loading initial data..."
    python manage.py loaddata initial_data.json
else
    echo "⚠️  No initial_data.json found, skipping..."
fi

# Crear superusuario automáticamente (opcional)
echo "👤 Creating superuser if needed..."
python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123');
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
" || echo "Could not create superuser, continuing..."

echo "🌐 Starting server on 0.0.0.0:8000..."
exec sh -c "python manage.py migrate && python manage.py loaddata initial_data.json && python manage.py runserver 0.0.0.0:8000"
