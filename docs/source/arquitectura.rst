==============
Arquitectura
==============

Descripción General
===================

QC Matrix Generator es un sistema escalable diseñado para:

1. **Gestión de Matrices de Testing** - Crear y ejecutar matrices de pruebas para diferentes equipos y dispositivos
2. **Chatbot de Soporte** - Asistente inteligente que responde preguntas basándose en documentación

Arquitectura de Alto Nivel
===========================

::

    ┌─────────────────────────────────────────────────────────────┐
    │                        USUARIOS                              │
    │         Web Browser          │         Streamlit Chat        │
    └──────────────┬────────────────┼───────────────┬──────────────┘
                   │                                 │
          ┌────────▼──────────┐          ┌──────────▼──────────┐
          │   Nginx Proxy     │          │  Streamlit App      │
          │  (Port 8080)      │          │  (Port 8501)        │
          └────────┬──────────┘          └──────────┬──────────┘
                   │                                 │
          ┌────────▼──────────────────────────────────▼─────────┐
          │           Django/Daphne (ASGI)                      │
          │              (Port 8000)                            │
          │                                                     │
          │  ┌──────────────┐  ┌──────────────────────────┐    │
          │  │ REST API     │  │ WebSocket Consumers      │    │
          │  │              │  │ (Django Channels)        │    │
          │  └──────┬───────┘  └──────┬───────────────────┘    │
          └─────────┼──────────────────┼──────────────────────────┘
                    │                  │
        ┌───────────▼──────────────────▼──────────────┐
        │           Redis                            │
        │    (Session, Cache, WebSocket Broker)     │
        │        (Port 6379)                        │
        └──────────────┬───────────────────────────────┘
                       │
        ┌──────────────▼──────────────┐
        │    PostgreSQL Database      │
        │   (Port 5432)               │
        │                             │
        │  - Users                    │
        │  - Teams (Equipos)          │
        │  - Devices                  │
        │  - Matrices                 │
        │  - Matrix Rows              │
        │  - Chat Messages            │
        └─────────────────────────────┘

        ┌─────────────────────────────┐
        │  Chroma Vector DB           │
        │  (RAG para Chat)            │
        │  (Almacena embeddings)      │
        └─────────────────────────────┘

        ┌─────────────────────────────┐
        │  Ollama / LLM               │
        │  (Motor de IA)              │
        │  (Local)                    │
        └─────────────────────────────┘

Stack Tecnológico
=================

**Backend**

- Django 4.x - Framework web
- Django REST Framework - APIs REST
- Django Channels - WebSockets
- Daphne - ASGI server
- Gunicorn / uWSGI - Application server

**Base de Datos**

- PostgreSQL - Base datos principal
- Redis - Cache, sesiones, WebSocket broker
- Chroma - Vector database (RAG)

**Frontend**

- HTML5 / CSS3 / JavaScript
- Streamlit - Chat UI
- WebSockets - Comunicación en tiempo real

**Otros**

- Docker / Docker Compose - Contenedorización
- Nginx - Reverse proxy
- WeasyPrint - Generación de PDFs
- OpenPyXL / Pandas - Manejo de Excel

Estructura de Directorios
==========================

::

    qc_matrix_generator/
    ├── main_website/              # Configuración global Django
    │   ├── settings/              # Settings por entorno (base, uat, prod)
    │   ├── asgi.py               # Configuración ASGI (WebSockets)
    │   ├── wsgi.py               # Configuración WSGI
    │   ├── urls.py               # URLs globales
    │   └── routing.py            # Rutas WebSocket
    │
    ├── app/                       # Apps del proyecto
    │   ├── accounts/              # Gestión de usuarios
    │   │   ├── models.py         # User, Equipo
    │   │   ├── views.py          # Login, registro
    │   │   ├── serializers.py    # API serializers
    │   │   └── urls.py
    │   │
    │   ├── matrix/                # App de seguimientos/matrices
    │   │   ├── models.py         # SuperMatriz, Matriz, Dispositivo
    │   │   ├── views.py          # CRUD de matrices
    │   │   ├── serializers.py    # API serializers
    │   │   ├── urls.py
    │   │   └── forms.py
    │   │
    │   └── ...
    │
    ├── chat_qc_soporte/           # App Streamlit de chat
    │   ├── app.py                # Aplicación principal
    │   ├── requirements.txt       # Dependencias Streamlit
    │   └── Dockerfile
    │
    ├── templates/                 # Templates HTML
    ├── static/                    # CSS, JS, imágenes
    ├── media/                     # Archivos subidos (PDFs, etc)
    │
    ├── docker-compose.yml         # Orquestación de servicios
    ├── Dockerfile                 # Imagen Django
    ├── requirements.txt           # Dependencias Python
    ├── manage.py                  # CLI de Django
    └── docs/                      # Documentación Sphinx

Flujo de Datos Principales
==========================

**1. Creación de Matriz**

::

    Usuario → Web UI → Django REST API → PostgreSQL
    ↓
    Guardar en DB → Validaciones → Response JSON

**2. Chat en Tiempo Real**

::

    Usuario escribe → WebSocket Conectado
    ↓
    Django Consumer recibe → Redis Broker
    ↓
    Streamlit/Ollama procesa → Response LLM
    ↓
    Redis → WebSocket → Usuario recibe

**3. Documento Upload para Chat**

::

    Usuario sube PDF → API REST
    ↓
    Procesar & Extraer texto
    ↓
    Generar embeddings (LLM)
    ↓
    Almacenar en Chroma Vector DB
    ↓
    Disponible para RAG

Componentes Principales
========================

**Django Application (app)**

- **accounts**: Autenticación y gestión de usuarios
- **matrix**: Modelos y vistas de matrices de testing
- APIs REST para todas las operaciones

**Streamlit Chat**

- Interfaz conversacional
- Integración con RAG (Retrieval-Augmented Generation)
- Ollama para generación de respuestas
- Chroma para búsqueda de documentos

**Proxy (Nginx)**

- Reverse proxy
- Load balancing
- Static files serving
- HTTPS termination (producción)

**WebSockets**

- Chat en tiempo real
- Notificaciones
- Actualizaciones en vivo

Flujo de Despliegue
===================

**Desarrollo (Local)**

::

    git checkout dev → python manage_local.py runserver

**UAT (Docker Compose)**

::

    git push → CI/CD → docker-compose build → docker-compose up

**Producción**

::

    git push (tag) → CI/CD → Build image → Push registry → Deploy

Consideraciones de Seguridad
=============================

- **Autenticación**: Django ORM + custom User model
- **Autorización**: Permisos por equipos
- **CORS**: django-cors-headers
- **HTTPS**: Nginx SSL (producción)
- **Secretos**: Variables de entorno (.env)
- **CSRF**: Django middleware
- **SQL Injection**: ORM de Django protege

Performance & Escalabilidad
============================

- **Cache**: Redis para sesiones y caché de consultas
- **WebSockets**: Escalable con Redis Channel Layer
- **DB**: PostgreSQL con índices optimizados
- **Static Files**: Servidos por Nginx/WhiteNoise
- **CDN**: Posible para assets (producción)

Monitoreo & Logging
===================

- Logs de Django en stdout/stderr
- Docker logs accesibles con `docker-compose logs`
- Health checks en docker-compose.yml
- Debug toolbar disponible en desarrollo
