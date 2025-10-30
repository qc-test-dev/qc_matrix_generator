========================
Docker y Redis
========================

Docker Compose
==============

Servicios
---------

El proyecto usa 4 servicios principales:

**1. PostgreSQL Database**

- Imagen: postgres:14
- Puerto: 5433 (local) → 5432 (contenedor)
- Usuario: qc_admin
- Contraseña: qc_admin_pass
- BD: qc_matrix
- Volumen: postgres_data

**2. Redis**

- Imagen: redis:6-alpine
- Puerto: 6380 (local) → 6379 (contenedor)
- Uso: Cache, sesiones, WebSocket broker
- Volumen: redis-data

**3. Django App (Daphne)**

- Build: ./Dockerfile
- Puerto: 8000 (contenedor)
- ASGI Server: Daphne
- Dependencias: db (PostgreSQL), redis
- Volumen: ./ (código)

**4. Nginx Proxy**

- Build: ./proxy_uat/Dockerfile
- Puerto: 8080 (local)
- Uso: Reverse proxy, static files
- Upstream: app:8000

**5. Streamlit Chat (Opcional)**

- Build: ./chat_qc_soporte/Dockerfile
- Puerto: 8501 (local)
- Uso: Chat LLM UI
- Dependencias: Ollama, Chroma

Comandos Docker Compose
=======================

**Levantar servicios**

::

    docker-compose up -d

**Ver servicios corriendo**

::

    docker-compose ps

**Ver logs en vivo**

::

    docker-compose logs -f app
    docker-compose logs -f db
    docker-compose logs -f redis

**Reconstruir imagen**

::

    docker-compose up -d --build

**Detener servicios**

::

    docker-compose down

**Eliminar volúmenes (⚠️ PERDERÁS DATOS)**

::

    docker-compose down -v

**Ejecutar comando en contenedor**

::

    docker-compose exec app python manage.py migrate
    docker-compose exec app python manage.py createsuperuser

**Re-crear contenedor específico**

::

    docker-compose up -d --force-recreate db

Variables de Entorno
====================

El archivo `docker-compose.yml` define variables que el contenedor usa.

Crear archivo `.env` en la raíz::

    # Django
    DEBUG=0
    SECRET_KEY=tu-clave-secreta-muy-segura
    ALLOWED_HOSTS=localhost,127.0.0.1,example.com

    # Database
    POSTGRES_DB=qc_matrix
    POSTGRES_USER=qc_admin
    POSTGRES_PASSWORD=qc_admin_pass
    POSTGRES_HOST=db
    POSTGRES_PORT=5432

    # Redis
    REDIS_HOST=redis
    REDIS_PORT=6379

    # JIRA Integration (opcional)
    JIRA_EMAIL=tu-email@atlassian.com
    JIRA_API_TOKEN=tu-token-jira

El docker-compose.yml las carga automáticamente.

Dockerfile
==========

Análisis del Dockerfile::

    FROM python:3.11-slim
    
    WORKDIR /app
    
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt
    
    COPY . .
    
    # Crear usuario no-root
    RUN useradd -m -u 1000 appuser && chown -R appuser /app
    USER appuser
    
    EXPOSE 8000
    
    CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "main_website.asgi:application"]

**Puntos clave:**

- Imagen base: python:3.11-slim (ligera)
- Instala requirements sin caché
- User no-root por seguridad
- Expone puerto 8000
- Inicia Daphne (ASGI server)

Volumes
=======

**postgres_data**

- Almacena datos de PostgreSQL
- Persisten entre reinicios
- Ubicación en host: /var/lib/docker/volumes/

**staticfiles-volume**

- Archivos estáticos de Django
- Compartidos entre app y nginx
- Creado por `collectstatic`

**Media**

- Archivos subidos (PDFs, etc)
- Mapeado: ./media → /app/media

Health Checks
=============

Cada servicio tiene un health check:

**PostgreSQL**

::

    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U qc_admin -d qc_matrix"]
      interval: 5s
      timeout: 5s
      retries: 5

**Redis**

::

    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

**Django App**

::

    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/"]
      interval: 30s
      timeout: 10s
      retries: 3

---

Redis
=====

¿Qué es Redis?
--------------

Redis es un almacén de datos en memoria (key-value) ultra-rápido.

En este proyecto lo usamos para:

- **Sesiones**: Almacenar datos de usuario logged in
- **Cache**: Guardar queries y resultados frecuentes
- **WebSocket Broker**: Comunicación real-time (Channels)

Configuración en Django
-----------------------

**settings.py**

::

    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": "redis://redis:6379/0",
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "CONNECTION_POOL_KWARGS": {
                    "max_connections": 50,
                    "retry_on_timeout": True
                }
            }
        }
    }

    # Django Channels
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [("redis", 6379)],
                "capacity": 1500,
                "expiry": 10,
            },
        },
    }

    # Sesiones en Redis
    SESSION_ENGINE = "django.contrib.sessions.backends.cache"
    SESSION_CACHE_ALIAS = "default"

Uso en Django
-------------

**Guardar en caché**

::

    from django.core.cache import cache
    
    cache.set('matriz_1_stats', datos, timeout=3600)  # 1 hora

**Obtener del caché**

::

    stats = cache.get('matriz_1_stats')
    if stats is None:
        # Calcular stats
        pass

**Eliminar del caché**

::

    cache.delete('matriz_1_stats')
    cache.delete_many(['key1', 'key2'])

**Limpiar todo el caché**

::

    cache.clear()

Monitoreo de Redis
------------------

**Conectarse a Redis CLI**

::

    docker-compose exec redis redis-cli

**Comandos útiles**

::

    PING                 # Verificar conexión
    INFO                 # Información del servidor
    DBSIZE               # Número de keys
    KEYS *               # Listar todas las keys
    GET key              # Obtener valor
    TYPE key             # Tipo de data
    TTL key              # Tiempo de expiración
    MONITOR              # Monitorear en vivo
    MEMORY STATS         # Uso de memoria

**Ver todas las keys en caché**

::

    KEYS *

**Ver session de usuario (ID=1)**

::

    KEYS "django.session.cache*"

**Monitoreo en vivo (ver todas las operaciones)**

::

    MONITOR

**Vaciar todo (⚠️ CUIDADO)**

::

    FLUSHALL

Troubleshooting
===============

**"Connection refused" en Redis**

::

    # Verificar que Redis está corriendo
    docker-compose ps redis
    
    # Ver logs
    docker-compose logs redis
    
    # Reiniciar
    docker-compose restart redis

**Memoria llena en Redis**

::

    # En redis-cli
    INFO memory
    
    # Limpiar
    docker-compose exec redis redis-cli FLUSHDB

**PostgreSQL no conecta**

::

    # Verificar
    docker-compose ps db
    
    # Ver logs
    docker-compose logs db
    
    # Reiniciar
    docker-compose restart db

**Puertos en conflicto**

Cambiar en docker-compose.yml::

    ports:
      - "8080:8080"    # Nginx
      - "5433:5432"    # PostgreSQL
      - "6380:6379"    # Redis

**Volúmenes llenos**

::

    # Limpiar volúmenes no usados
    docker volume prune

Performance Tuning
==================

**Redis - Aumentar límite de conexiones**

::

    docker-compose exec redis redis-cli config set maxclients 10000

**Redis - Política de evicción (cuando se llena)**

::

    docker-compose exec redis redis-cli config set maxmemory-policy allkeys-lru

Políticas::

    - noeviction        # No eliminar (retorna error)
    - allkeys-lru       # Eliminar keys menos usadas
    - allkeys-lfu       # Eliminar keys menos frecuentes
    - volatile-lru      # Eliminar keys con TTL menos usadas
    - volatile-lfu      # Eliminar keys con TTL menos frecuentes

**PostgreSQL - Aumentar connections**

En docker-compose.yml::

    environment:
      POSTGRES_INIT_ARGS: "-c max_connections=200"

Backup y Restore
================

**Backup de PostgreSQL**

::

    docker-compose exec db pg_dump -U qc_admin qc_matrix > backup.sql

**Restore de PostgreSQL**

::

    cat backup.sql | docker-compose exec -T db psql -U qc_admin qc_matrix

**Backup de Redis**

::

    docker-compose exec redis redis-cli SAVE
    docker cp <container_id>:/data/dump.rdb ./backup_redis.rdb

**Restore de Redis**

::

    docker cp ./backup_redis.rdb <container_id>:/data/dump.rdb
    docker-compose restart redis

Producción vs Desarrollo
========================

**Desarrollo (docker-compose.yml)**

- DEBUG=True
- SQLite/PostgreSQL local
- Redis local
- Sin HTTPS
- Sin nginx

**Producción (docker-compose-deploy.yml)**

- DEBUG=False
- PostgreSQL en RDS
- Redis managed
- HTTPS habilitado
- Nginx + gunicorn
- Secrets en variables de entorno

Escalado
========

Para escalar el sistema en producción:

1. **PostgreSQL**: RDS en AWS / Cloud SQL en GCP
2. **Redis**: ElastiCache / Redis Cloud
3. **Django App**: Kubernetes / ECS con load balancer
4. **Static Files**: S3 / Google Cloud Storage
5. **CDN**: CloudFront / Cloudflare
