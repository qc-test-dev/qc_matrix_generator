==============
API REST
==============

Autenticación
=============

Todas las requests (excepto login/register) requieren autenticación.

**Tipos de autenticación**

1. **Token Authentication** (recomendado para APIs)

Header::

    Authorization: Token abc123def456

2. **Session Authentication** (para navegador)

Cookie:: 

    sessionid=xyz123...

Endpoints de Autenticación
===========================

**Obtener Token**

**POST** ``/api-auth/login/``

Body::

    {
        "username": "usuario",
        "password": "contraseña"
    }

Response (200 OK)::

    {
        "token": "abc123def456",
        "user": {
            "id": 1,
            "username": "usuario",
            "nombre": "Juan",
            "apellido": "Pérez",
            "cargo": "TESTER",
            "equipo": "Android"
        }
    }

**Logout**

**POST** ``/api-auth/logout/``

Headers:: 

    Authorization: Token abc123def456

Response (200 OK)::

    {
        "message": "Successfully logged out"
    }

---

App: Matrix - Endpoints
========================

**SuperMatriz**
--------------

Listar SuperMatrices
^^^^^^^^^^^^^^^^^^^^^

**GET** ``/api/matrix/supermatriz/``

Query Parameters::

    ?page=1              # Paginación
    ?search=nombre       # Búsqueda por nombre
    ?equipo_id=1         # Filtrar por equipo
    ?archivado=false     # Mostrar no archivadas

Response (200 OK)::

    {
        "count": 25,
        "next": "http://api/matrix/supermatriz/?page=2",
        "previous": null,
        "results": [
            {
                "id": 1,
                "nombre": "Project Q1 2025",
                "descripcion": "Testing de Q1",
                "fecha_creacion": "2025-01-15T10:30:00Z",
                "fecha_fin": "2025-03-31",
                "equipo_nuevo": {
                    "id": 1,
                    "nombre": "Android"
                },
                "archivado": false,
                "matrices_count": 5
            },
            ...
        ]
    }

Crear SuperMatriz
^^^^^^^^^^^^^^^^^^

**POST** ``/api/matrix/supermatriz/``

Body::

    {
        "nombre": "Project Q2 2025",
        "descripcion": "Testing de Q2",
        "equipo_nuevo": 2,
        "fecha_fin": "2025-06-30"
    }

Response (201 Created)::

    {
        "id": 26,
        "nombre": "Project Q2 2025",
        "descripcion": "Testing de Q2",
        "fecha_creacion": "2025-10-28T14:00:00Z",
        "fecha_fin": "2025-06-30",
        "equipo_nuevo": 2,
        "archivado": false
    }

Actualizar SuperMatriz
^^^^^^^^^^^^^^^^^^^^^^^

**PATCH** ``/api/matrix/supermatriz/{id}/``

Body (parcial)::

    {
        "nombre": "Project Q2 2025 - Updated",
        "archivado": true
    }

Response (200 OK)::

    {
        "id": 26,
        "nombre": "Project Q2 2025 - Updated",
        ...
    }

Eliminar SuperMatriz
^^^^^^^^^^^^^^^^^^^^

**DELETE** ``/api/matrix/supermatriz/{id}/``

Response (204 No Content)

---

**Matriz**
---------

Listar Matrices
^^^^^^^^^^^^^^^

**GET** ``/api/matrix/matriz/``

Query Parameters::

    ?super_matriz_id=1   # Filtrar por proyecto
    ?dispositivo_id=1    # Filtrar por dispositivo
    ?search=nombre       # Búsqueda

Response (200 OK)::

    {
        "count": 50,
        "next": "http://api/matrix/matriz/?page=2",
        "previous": null,
        "results": [
            {
                "id": 1,
                "nombre": "Matriz Android - Login",
                "super_matriz": {
                    "id": 1,
                    "nombre": "Project Q1 2025"
                },
                "dispositivo": {
                    "id": 5,
                    "nombre": "Samsung Galaxy S21"
                },
                "fecha_creacion": "2025-01-20T11:00:00Z",
                "alcances_utilizados": "Login, Register",
                "total_casos": 15,
                "casos_pass": 14,
                "casos_fail": 1
            },
            ...
        ]
    }

Crear Matriz
^^^^^^^^^^^^

**POST** ``/api/matrix/matriz/``

Body::

    {
        "nombre": "Matriz Android - Payment",
        "super_matriz": 1,
        "dispositivo": 5,
        "alcances_utilizados": "Payment Flow"
    }

Response (201 Created)::

    {
        "id": 51,
        "nombre": "Matriz Android - Payment",
        "super_matriz": 1,
        "dispositivo": 5,
        "fecha_creacion": "2025-10-28T15:30:00Z",
        "alcances_utilizados": "Payment Flow",
        "total_casos": 0
    }

Obtener Detalle de Matriz
^^^^^^^^^^^^^^^^^^^^^^^^^^

**GET** ``/api/matrix/matriz/{id}/``

Response (200 OK)::

    {
        "id": 1,
        "nombre": "Matriz Android - Login",
        "super_matriz": {...},
        "dispositivo": {...},
        "fecha_creacion": "2025-01-20T11:00:00Z",
        "alcances_utilizados": "Login, Register",
        "filas": [
            {
                "id": 1,
                "numero_caso": 1,
                "descripcion_del_caso": "Valid login",
                "precondiciones": "App installed",
                "pasos_a_validar": "Enter credentials",
                "resultado_esperado": "Login success",
                "resultado_actual": "Login success",
                "estatus_caso": "PASS"
            },
            ...
        ]
    }

---

**MatrizRow (Casos de Prueba)**
------------------------------

Listar Casos
^^^^^^^^^^^^

**GET** ``/api/matrix/matrizrow/?matriz_id=1``

Query Parameters::

    ?matriz_id=1         # REQUERIDO - Matriz padre
    ?estatus_caso=PASS   # Filtrar por estado

Response (200 OK)::

    {
        "count": 15,
        "results": [
            {
                "id": 1,
                "numero_caso": 1,
                "descripcion_del_caso": "Valid login with email",
                "precondiciones": "App installed and clean",
                "pasos_a_validar": "1. Open app\n2. Enter email\n3. Enter password\n4. Click login",
                "resultado_esperado": "User logged in successfully",
                "resultado_actual": "User logged in successfully",
                "estatus_caso": "PASS",
                "tipo_validacion": "Functional",
                "ambiente": "QA"
            },
            ...
        ]
    }

Crear Caso
^^^^^^^^^^

**POST** ``/api/matrix/matrizrow/``

Body::

    {
        "matriz": 1,
        "numero_caso": 16,
        "descripcion_del_caso": "Invalid email format",
        "precondiciones": "App installed",
        "pasos_a_validar": "Enter invalid email",
        "resultado_esperado": "Error message displayed",
        "tipo_validacion": "Validation",
        "ambiente": "QA"
    }

Response (201 Created)::

    {
        "id": 16,
        "numero_caso": 16,
        "descripcion_del_caso": "Invalid email format",
        "estatus_caso": "PENDIENTE",
        "fecha_creacion": "2025-10-28T16:00:00Z",
        ...
    }

Actualizar Caso (Resultado)
^^^^^^^^^^^^^^^^^^^^^^^^^^^

**PATCH** ``/api/matrix/matrizrow/{id}/``

Body::

    {
        "resultado_actual": "Error message NOT displayed",
        "estatus_caso": "FAIL"
    }

Response (200 OK)::

    {
        "id": 16,
        "estatus_caso": "FAIL",
        "resultado_actual": "Error message NOT displayed",
        ...
    }

---

**Dispositivo**
--------------

Listar Dispositivos
^^^^^^^^^^^^^^^^^^^

**GET** ``/api/matrix/dispositivo/?equipo_id=1``

Response (200 OK)::

    {
        "count": 10,
        "results": [
            {
                "id": 1,
                "nombre": "Samsung Galaxy S21",
                "equipo": {
                    "id": 1,
                    "nombre": "Android"
                },
                "matriz_base": "matriz_base_android",
                "operativo": true,
                "excel_url": "/static/excel_files/matriz_base_android.xlsx"
            },
            ...
        ]
    }

---

**Estadísticas**
----------------

Resumen de Matriz
^^^^^^^^^^^^^^^^^

**GET** ``/api/matrix/matriz/{id}/statistics/``

Response (200 OK)::

    {
        "total_casos": 15,
        "casos_pass": 14,
        "casos_fail": 1,
        "casos_pendiente": 0,
        "casos_no_aplica": 0,
        "porcentaje_pass": 93.33,
        "porcentaje_fail": 6.67
    }

Resumen de SuperMatriz
^^^^^^^^^^^^^^^^^^^^^^

**GET** ``/api/matrix/supermatriz/{id}/statistics/``

Response (200 OK)::

    {
        "total_matrices": 5,
        "total_casos": 75,
        "casos_pass": 71,
        "casos_fail": 4,
        "porcentaje_ejecucion": 100,
        "por_dispositivo": [
            {
                "dispositivo": "Samsung Galaxy S21",
                "total": 15,
                "pass": 14,
                "fail": 1
            }
        ]
    }

---

Errores HTTP
============

**400 Bad Request**

::

    {
        "error": "Invalid input",
        "details": {
            "campo": ["Error message"]
        }
    }

**401 Unauthorized**

::

    {
        "detail": "Authentication credentials were not provided."
    }

**403 Forbidden**

::

    {
        "detail": "You do not have permission to perform this action."
    }

**404 Not Found**

::

    {
        "detail": "Not found."
    }

**500 Server Error**

::

    {
        "error": "Internal server error"
    }

---

Límites de API
==============

- **Rate limit**: 1000 requests/hour (por usuario)
- **Timeout**: 30 segundos
- **Max page size**: 100 items

---

Ejemplos con cURL
==================

**Login**

::

    curl -X POST http://localhost:8081/api-auth/login/ \
      -H "Content-Type: application/json" \
      -d '{
        "username": "admin",
        "password": "admin123"
      }'

**Listar SuperMatrices**

::

    curl -X GET http://localhost:8081/api/matrix/supermatriz/ \
      -H "Authorization: Token abc123"

**Crear Matriz**

::

    curl -X POST http://localhost:8081/api/matrix/matriz/ \
      -H "Authorization: Token abc123" \
      -H "Content-Type: application/json" \
      -d '{
        "nombre": "Test Matriz",
        "super_matriz": 1,
        "dispositivo": 5
      }'

---

WebSocket - Chat en Tiempo Real
===============================

El sistema incluye WebSockets para chat en tiempo real usando Django Channels.

**Conectar**

::

    ws://localhost:8081/ws/chat/room1/

**Enviar Mensaje (JSON)**

::

    {
        "message": "¿Cuál es el proceso de login?"
    }

**Recibir Respuesta (JSON)**

::

    {
        "type": "chat_message",
        "user": "chatbot",
        "message": "El proceso es...",
        "timestamp": "2025-10-28T16:30:00Z"
    }

JavaScript Client::

    const socket = new WebSocket('ws://localhost:8081/ws/chat/room1/');
    
    socket.onopen = () => {
        socket.send(JSON.stringify({message: 'Hola'}));
    };
    
    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log(data.message);
    };
