#!/bin/bash
set -e  # Salir si hay errores

# Variables por defecto
POSTGRES_HOST=${POSTGRES_HOST:-db}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
REDIS_HOST=${REDIS_HOST:-redis}
REDIS_PORT=${REDIS_PORT:-6379}

# Colores para logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}[INICIO] Iniciando aplicación Django con WebSocket...${NC}"

# Función para esperar que la base de datos esté lista
wait_for_db() {
    echo -e "${YELLOW}[DB] Esperando PostgreSQL en $POSTGRES_HOST:$POSTGRES_PORT...${NC}"
    while ! nc -z "$POSTGRES_HOST" "$POSTGRES_PORT" 2>/dev/null; do
        echo -e "${YELLOW}[DB] PostgreSQL no está listo - esperando...${NC}"
        sleep 1
    done
    echo -e "${GREEN}[DB] PostgreSQL está disponible!${NC}"
}

# Función para esperar que Redis esté listo
wait_for_redis() {
    echo -e "${YELLOW}[REDIS] Esperando Redis en $REDIS_HOST:$REDIS_PORT...${NC}"
    while ! nc -z "$REDIS_HOST" "$REDIS_PORT" 2>/dev/null; do
        echo -e "${YELLOW}[REDIS] Redis no está listo - esperando...${NC}"
        sleep 1
    done
    echo -e "${GREEN}[REDIS] Redis está disponible!${NC}"
}

# Esperar servicios
wait_for_db
wait_for_redis

# Estabilización
echo -e "${YELLOW}[SETUP] Esperando estabilización de servicios...${NC}"
sleep 2

# Migraciones
echo -e "${YELLOW}[SETUP] Ejecutando migraciones...${NC}"
python manage.py makemigrations --noinput
python manage.py migrate --noinput

# Collectstatic
echo -e "${YELLOW}[SETUP] Recolectando archivos estáticos...${NC}"
python manage.py collectstatic --noinput --clear

# Datos iniciales
if [ -f "/app/initialdata.json" ]; then
    echo -e "${YELLOW}[SETUP] Cargando datos iniciales...${NC}"
    python manage.py loaddata /app/initialdata.json --ignorenonexistent || true
fi

# Iniciar Daphne
# Iniciar Daphne
echo -e "${GREEN}[SERVER] Iniciando Daphne en 0.0.0.0:8000...${NC}"
echo -e "${GREEN}[SERVER] WebSocket habilitado${NC}"
exec daphne -b 0.0.0.0 -p 8000 -v 2 main_website.asgi:application