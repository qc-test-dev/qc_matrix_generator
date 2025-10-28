=======================
Inicio Rápido
=======================

Requisitos del Sistema
======================

- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- Docker & Docker Compose (recomendado)
- Git

Instalación Local (sin Docker)
==============================

1. Clonar el repositorio
-----------------------

::

    git clone https://github.com/qc-test-dev/qc_matrix_generator.git
    cd qc_matrix_generator
    git checkout dev

2. Crear entorno virtual
------------------------

::

    python -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate

3. Instalar dependencias
------------------------

::

    pip install -r requirements.txt

4. Configurar variables de entorno
----------------------------------

Crear archivo `.env` en la raíz::

    DEBUG=True
    SECRET_KEY=tu-clave-secreta-desarrollo
    ALLOWED_HOSTS=localhost,127.0.0.1

    # Database
    POSTGRES_DB=qc_matrix
    POSTGRES_USER=qc_admin
    POSTGRES_PASSWORD=qc_admin_pass
    POSTGRES_HOST=localhost
    POSTGRES_PORT=5432

    # Redis
    REDIS_HOST=localhost
    REDIS_PORT=6379

    # JIRA (opcional)
    JIRA_EMAIL=tu-email@example.com
    JIRA_API_TOKEN=tu-token-jira

5. Inicializar base de datos
-----------------------------

::

    python manage_local.py migrate
    python manage_local.py createsuperuser
    python manage_local.py collectstatic --noinput

6. Ejecutar servidor
--------------------

Terminal 1 - Servidor Daphne (ASGI)::

    daphne -e tcp:port=8081:interface=127.0.0.1 main_website.asgi:application

Terminal 2 - Redis::

    redis-server

Terminal 3 - Streamlit Chat (opcional)::

    cd chat_qc_soporte
    streamlit run app.py

**Acceder a:**

- Web: http://127.0.0.1:8081
- Admin: http://127.0.0.1:8081/admin
- Chat: http://localhost:8501

---

Instalación con Docker Compose
===============================

**1. Asegurarse de tener Docker instalado**

::

    docker --version
    docker-compose --version

**2. Crear red Docker (una sola vez)**

::

    docker network create qc_network

**3. Levantar servicios**

::

    docker-compose up -d

**4. Verificar estado**

::

    docker-compose ps

**5. Ver logs**

::

    docker-compose logs -f app

**6. Acceder a la aplicación**

- Web: http://localhost:8080
- Admin: http://localhost:8080/admin
- Chat: http://localhost:8501
- DB Admin: http://localhost:5433 (pgAdmin si está configurado)

---

Primeros Pasos Después de Instalar
==================================

**1. Crear superusuario (si no lo hizo)**

::

    python manage_local.py createsuperuser
    # o en Docker:
    docker-compose exec app python manage.py createsuperuser

**2. Acceder al admin de Django**

- URL: http://localhost:8081/admin (local) o http://localhost:8080/admin (Docker)
- Usar credenciales del superusuario

**3. Crear equipos en el admin**

Ir a: Admin → Equipos

Crear equipos como:

- Claro TV STB - IPTV - Roku - TATA
- STV (LG,Samsung,ADR), Kepler-FireTV, STV2(Hisense,Netrange)
- IPTV AOSP
- WIN - WEB - Fire TV
- IOS - TvOS
- Android
- Smart TV AAF

**4. Crear usuarios de prueba**

- Ir a: Admin → Users
- Crear usuarios con equipos asignados
- Roles: Lider o Tester

**5. Crear dispositivos de prueba**

- Ir a: Admin → Dispositivos
- Crear dispositivos para cada equipo

**6. Generar primera matriz**

- Acceder a: http://localhost:8081/matrix/
- Click en "Nueva Matriz"
- Seleccionar equipo y dispositivo
- Crear matriz

---

Troubleshooting
===============

**Error: Connection refused (PostgreSQL)**

::

    # Verificar que PostgreSQL está corriendo
    sudo systemctl status postgresql
    # o en Docker:
    docker-compose logs db

**Error: Redis connection failed**

::

    # Verificar Redis
    redis-cli ping  # Debería responder: PONG
    # o en Docker:
    docker-compose logs redis

**Puerto ya en uso (8081, 5432, 6379)**

::

    # Cambiar puerto en settings.py o docker-compose.yml
    # Ejemplo Docker:
    ports:
      - "8081:8000"  # puerto_local:puerto_contenedor

**Migraciones pendientes**

::

    python manage_local.py makemigrations
    python manage_local.py migrate

**Limpiar caché**

::

    python manage_local.py clear_cache
    redis-cli FLUSHDB

---

Recursos Útiles
===============

- Documentación de Django: https://docs.djangoproject.com/
- DRF (Django REST Framework): https://www.django-rest-framework.org/
- Django Channels: https://channels.readthedocs.io/
- Streamlit: https://docs.streamlit.io/
- PostgreSQL: https://www.postgresql.org/docs/
- Redis: https://redis.io/docs/
