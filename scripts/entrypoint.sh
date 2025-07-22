#!/bin/bash

# Colores para logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}[INICIO] Iniciando aplicación Django con WebSocket...${NC}"

# Función para esperar que la base de datos esté lista
wait_for_db() {
    echo -e "${YELLOW}[DB] Esperando que PostgreSQL esté disponible...${NC}"
    while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
        echo -e "${YELLOW}[DB] PostgreSQL no está listo - esperando...${NC}"
        sleep 1
    done
    echo -e "${GREEN}[DB] PostgreSQL está disponible!${NC}"
}

# Función para esperar que Redis esté listo
wait_for_redis() {
    echo -e "${YELLOW}[REDIS] Esperando que Redis esté disponible...${NC}"
    while ! nc -z $REDIS_HOST $REDIS_PORT; do
        echo -e "${YELLOW}[REDIS] Redis no está listo - esperando...${NC}"
        sleep 1
    done
    echo -e "${GREEN}[REDIS] Redis está disponible!${NC}"
}

# Esperar servicios
wait_for_db
wait_for_redis

# Dar un poco más de tiempo para que los servicios se estabilicen
echo -e "${YELLOW}[SETUP] Esperando estabilización de servicios...${NC}"
sleep 5

# Ejecutar migraciones
echo -e "${YELLOW}[SETUP] Ejecutando makemigrations...${NC}"
if python manage.py makemigrations; then
    echo -e "${GREEN}[SETUP] Makemigrations completado${NC}"
else
    echo -e "${RED}[ERROR] Error en makemigrations${NC}"
    exit 1
fi

echo -e "${YELLOW}[SETUP] Ejecutando migrate...${NC}"
if python manage.py migrate; then
    echo -e "${GREEN}[SETUP] Migrate completado${NC}"
else
    echo -e "${RED}[ERROR] Error en migrate${NC}"
    exit 1
fi

# Collectstatic
echo -e "${YELLOW}[SETUP] Ejecutando collectstatic...${NC}"
if python manage.py collectstatic --noinput --clear; then
    echo -e "${GREEN}[SETUP] Collectstatic completado${NC}"
else
    echo -e "${RED}[ERROR] Error en collectstatic${NC}"
    exit 1
fi

# Cargar datos iniciales si existen
if [ -f /app/initialdata.json ]; then
    echo -e "${YELLOW}[SETUP] Cargando datos iniciales...${NC}"
    if python manage.py loaddata /app/initialdata.json --ignorenonexistent --exclude contenttypes --exclude auth.permission; then
        echo -e "${GREEN}[SETUP] Datos iniciales cargados${NC}"
    else
        echo -e "${YELLOW}[WARNING] Error al cargar datos iniciales (continuando)${NC}"
    fi
else
    echo -e "${YELLOW}[SETUP] No se encontró initialdata.json${NC}"
fi

# ✅ WEBSOCKET: Usar Daphne con ASGI
echo -e "${GREEN}[SERVER] Iniciando servidor Daphne con WebSocket...${NC}"
exec daphne -b 0.0.0.0 -p 8000  main_website.asgi:application