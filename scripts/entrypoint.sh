#!/bin/bash
set -e

POSTGRES_HOST=${POSTGRES_HOST:-db}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
REDIS_HOST=${REDIS_HOST:-redis}
REDIS_PORT=${REDIS_PORT:-6379}

echo -e "\033[1;34m[INICIO] Iniciando aplicación Django con WebSocket...\033[0m"

wait_for_service() {
    local host=$1
    local port=$2
    echo -e "\033[1;33m[ESPERA] Esperando servicio en $host:$port...\033[0m"
    while ! nc -z "$host" "$port"; do
        echo -e "\033[1;33m[ESPERA] Servicio $host:$port no disponible, esperando...\033[0m"
        sleep 2
    done
    echo -e "\033[1;32m[OK] Servicio $host:$port disponible!\033[0m"
}

wait_for_service "$POSTGRES_HOST" "$POSTGRES_PORT"
wait_for_service "$REDIS_HOST" "$REDIS_PORT"

echo -e "\033[1;33m[SETUP] Ejecutando migraciones...\033[0m"
python manage.py makemigrations --noinput
python manage.py migrate --noinput

echo -e "\033[1;33m[SETUP] Recolectando archivos estáticos...\033[0m"
python manage.py collectstatic --noinput --clear

echo -e "\033[1;32m[SERVER] Iniciando Daphne en 0.0.0.0:8000...\033[0m"
exec daphne -b 0.0.0.0 -p 8000 -v 2 main_website.asgi:application
