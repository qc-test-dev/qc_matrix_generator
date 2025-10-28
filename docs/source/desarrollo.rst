====================
Guía de Desarrollo
====================

Entorno de Desarrollo Local
============================

**1. Clonar repositorio**

::

    git clone https://github.com/qc-test-dev/qc_matrix_generator.git
    cd qc_matrix_generator
    git checkout dev

**2. Crear entorno virtual**

::

    python -m venv venv
    source venv/bin/activate          # Linux/Mac
    # o
    venv\Scripts\activate             # Windows

**3. Instalar dependencias**

::

    pip install -r requirements.txt

**4. Configurar entorno local**

Crear `.env` en la raíz::

    DEBUG=True
    SECRET_KEY=dev-only-secret-key
    ALLOWED_HOSTS=localhost,127.0.0.1

    POSTGRES_DB=qc_matrix_dev
    POSTGRES_USER=postgres
    POSTGRES_PASSWORD=password
    POSTGRES_HOST=localhost
    POSTGRES_PORT=5432

    REDIS_HOST=localhost
    REDIS_PORT=6379

**5. Inicializar base de datos**

::

    python manage_local.py migrate

**6. Crear superusuario**

::

    python manage_local.py createsuperuser

**7. Ejecutar servidor de desarrollo**

::

    python manage_local.py runserver 0.0.0.0:8081

Acceder en: http://127.0.0.1:8081

Estructura del Código
====================

::

    app/
    ├── accounts/
    │   ├── models.py           # User, Equipo
    │   ├── views.py            # Auth views
    │   ├── serializers.py      # DRF serializers
    │   ├── urls.py
    │   └── forms.py
    │
    ├── matrix/
    │   ├── models.py           # SuperMatriz, Matriz, MatrizRow, Dispositivo
    │   ├── views.py            # CRUD views
    │   ├── serializers.py      # API serializers
    │   ├── urls.py
    │   ├── forms.py
    │   └── tests.py
    │
    └── ... (otras apps)

    main_website/
    ├── settings/
    │   ├── base.py             # Configuración base
    │   ├── uat.py              # UAT settings
    │   └── prod.py             # Producción
    ├── urls.py                 # URLs globales
    ├── asgi.py                 # ASGI + WebSockets
    └── wsgi.py

Workflow de Desarrollo
======================

**1. Crear rama para feature**

::

    git checkout -b feature/nombre-descriptivo

Ejemplos de nombres::

    feature/add-matriz-api
    feature/improve-performance
    bugfix/fix-login-issue
    docs/update-readme

**2. Hacer cambios en el código**

**3. Tests (si es aplicable)**

::

    python manage.py test app_name

**4. Linting y formato**

::

    # Verificar estilo
    flake8 app/

    # Formatear código
    black app/

    # Ordenar imports
    isort app/

**5. Commit**

::

    git add .
    git commit -m "feature: descripción clara del cambio"

**Convenciones de commit**

::

    feature: nueva funcionalidad
    bugfix: corrección de bug
    docs: cambios en documentación
    refactor: refactorización sin cambios funcionales
    perf: mejoras de performance
    style: cambios de formato/estilo

**6. Push a rama de feature**

::

    git push origin feature/nombre-descriptivo

**7. Crear Pull Request**

En GitHub:
- Ir a "Pull Requests"
- Click "New Pull Request"
- Seleccionar rama
- Agregar descripción
- Request review

**8. Merge a dev**

Una vez aprobado, mergear a `dev`.

Modelos y Migraciones
=====================

**Después de cambiar un modelo**

::

    python manage.py makemigrations

**Ver migraciones pendientes**

::

    python manage.py showmigrations

**Aplicar migraciones**

::

    python manage.py migrate

**Revertir migraciones**

::

    python manage.py migrate app_name 0001_initial

**Ver SQL de una migración**

::

    python manage.py sqlmigrate app_name 0001

Crear Nuevas Apps
=================

**Generar app**

::

    python manage.py startapp nombre_app

Esto crea la estructura básica. Luego:

1. Crear modelos en `models.py`
2. Registrar en `admin.py`
3. Crear serializers en `serializers.py`
4. Crear views/viewsets en `views.py`
5. Crear urls en `urls.py`
6. Agregar a `INSTALLED_APPS` en settings

APIs con DRF
============

**Crear Serializer**

::

    from rest_framework import serializers
    from .models import Matriz

    class MatrizSerializer(serializers.ModelSerializer):
        class Meta:
            model = Matriz
            fields = ['id', 'nombre', 'super_matriz', 'dispositivo']

**Crear ViewSet**

::

    from rest_framework import viewsets
    from .models import Matriz
    from .serializers import MatrizSerializer

    class MatrizViewSet(viewsets.ModelViewSet):
        queryset = Matriz.objects.all()
        serializer_class = MatrizSerializer
        
        def get_queryset(self):
            # Filtro opcional
            return self.queryset.filter(usuario=self.request.user)

**Registrar URLs**

::

    from rest_framework.routers import DefaultRouter
    from .views import MatrizViewSet

    router = DefaultRouter()
    router.register('matriz', MatrizViewSet)

    urlpatterns = router.urls

WebSockets
==========

**Crear Consumer**

::

    from channels.generic.websocket import AsyncWebsocketConsumer
    import json

    class ChatConsumer(AsyncWebsocketConsumer):
        async def connect(self):
            self.room_name = self.scope['url_route']['kwargs']['room_name']
            self.room_group_name = f'chat_{self.room_name}'

            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()

        async def disconnect(self, close_code):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

        async def receive(self, text_data):
            message = json.loads(text_data)
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message['message'],
                    'user': self.scope['user'].username
                }
            )

        async def chat_message(self, event):
            await self.send(text_data=json.dumps({
                'message': event['message'],
                'user': event['user']
            }))

**Registrar Consumer**

En `main_website/routing.py`::

    from django.urls import path
    from channels.routing import ProtocolTypeRouter, URLRouter
    from channels.auth import AuthMiddlewareStack
    from app.matrix.consumers import ChatConsumer

    application = ProtocolTypeRouter({
        "websocket": AuthMiddlewareStack(
            URLRouter([
                path("ws/chat/<str:room_name>/", ChatConsumer.as_asgi()),
            ])
        ),
    })

Testing
=======

**Crear tests**

::

    from django.test import TestCase
    from app.matrix.models import Matriz, SuperMatriz

    class MatrizTestCase(TestCase):
        def setUp(self):
            self.super_matriz = SuperMatriz.objects.create(
                nombre="Test Project"
            )

        def test_create_matriz(self):
            matriz = Matriz.objects.create(
                nombre="Test Matriz",
                super_matriz=self.super_matriz
            )
            self.assertEqual(matriz.nombre, "Test Matriz")

        def test_matriz_str(self):
            matriz = Matriz.objects.create(
                nombre="Test Matriz",
                super_matriz=self.super_matriz
            )
            self.assertEqual(str(matriz), "Test Matriz")

**Ejecutar tests**

::

    python manage.py test                         # Todos
    python manage.py test app.matrix              # De una app
    python manage.py test app.matrix.tests.MatrizTestCase  # Específico
    python manage.py test --keepdb                # Sin recrear BD

**Coverage**

::

    pip install coverage
    coverage run --source='.' manage.py test
    coverage report
    coverage html                                 # Genera reporte HTML

Debugging
=========

**Django Shell (REPL interactivo)**

::

    python manage.py shell

Útil para probar queries::

    from app.matrix.models import Matriz
    
    # Ver todas las matrices
    Matriz.objects.all()
    
    # Ver matriz con ID 1
    m = Matriz.objects.get(id=1)
    
    # Acceder a relaciones
    m.super_matriz.nombre
    m.filas.all()

**Logs**

En `settings.py`::

    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
            },
        },
        'root': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    }

En el código::

    import logging
    logger = logging.getLogger(__name__)
    
    logger.debug("Mensaje debug")
    logger.info("Información")
    logger.warning("Advertencia")
    logger.error("Error: " + str(e))

**Django Debug Toolbar**

::

    pip install django-debug-toolbar

En `settings.py`::

    INSTALLED_APPS = [..., 'debug_toolbar']
    MIDDLEWARE = [..., 'debug_toolbar.middleware.DebugToolbarMiddleware']
    INTERNAL_IPS = ['127.0.0.1']

Luego acceder a http://127.0.0.1:8081/

Comandos Útiles
===============

**Crear datos de prueba (fixtures)**

::

    python manage.py dumpdata app.matriz > fixtures.json
    python manage.py loaddata fixtures.json

**Vaciar tabla**

::

    python manage.py sqlclear app.matriz

**Ver SQL de una query**

::

    from django.db import connection
    from app.matrix.models import Matriz
    
    Matriz.objects.all().query
    print(connection.queries)

**Análisis de rendimiento**

::

    from django.db import connection
    from django.test.utils import CaptureQueriesContext
    
    with CaptureQueriesContext(connection) as context:
        Matriz.objects.all()
    
    print(f"Queries: {len(context)}")
    for query in context:
        print(query['sql'])

Estándares de Código
====================

**PEP 8**

- Máximo 79 caracteres por línea
- Nombres en snake_case (variables, funciones)
- Nombres en PascalCase (clases)
- 2 líneas en blanco entre funciones
- 1 línea en blanco entre métodos

**Docstrings**

::

    def crear_matriz(super_matriz_id, nombre):
        """
        Crea una nueva matriz de testing.
        
        Args:
            super_matriz_id (int): ID de la SuperMatriz
            nombre (str): Nombre de la matriz
            
        Returns:
            Matriz: La matriz creada
            
        Raises:
            SuperMatriz.DoesNotExist: Si no existe la SuperMatriz
        """
        super_matriz = SuperMatriz.objects.get(id=super_matriz_id)
        return Matriz.objects.create(super_matriz=super_matriz, nombre=nombre)

**Type Hints** (recomendado)

::

    from typing import Optional
    
    def obtener_matriz(id: int) -> Optional[Matriz]:
        """Obtiene una matriz por ID."""
        return Matriz.objects.filter(id=id).first()

Recursos Útiles
===============

- Django Docs: https://docs.djangoproject.com/
- DRF: https://www.django-rest-framework.org/
- Channels: https://channels.readthedocs.io/
- Channels Testing: https://channels.readthedocs.io/en/latest/topics/testing.html
- PostgreSQL Docs: https://www.postgresql.org/docs/
- Redis Docs: https://redis.io/docs/
- Pytest: https://docs.pytest.org/

Desarrollo Remoto (SSH)
========================

**Conectar a servidor remoto**

::

    ssh user@server.com
    cd /app
    git pull origin dev
    python manage.py migrate
    systemctl restart django  # si está instalado como servicio

**Sync local → remoto con rsync**

::

    rsync -avz --exclude=venv --exclude=db.sqlite3 . user@server.com:/app/

**Reverse tunnel para debugging**

::

    ssh -R 5678:127.0.0.1:5678 user@server.com
    # Luego conectar debugger a localhost:5678 del servidor
