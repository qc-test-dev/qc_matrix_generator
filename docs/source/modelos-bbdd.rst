====================
Modelos y Base de Datos
====================

Diagrama Entidad-Relación (ER)
==============================

::

    ┌──────────────────┐
    │      User        │
    ├──────────────────┤
    │ id (PK)          │
    │ username (U)     │
    │ password         │
    │ nombre           │
    │ apellido         │
    │ cargo            │
    │ is_staff         │
    │ equipo_nuevo_id  │◄─────┐
    │ (FK)             │      │
    └────────┬─────────┘      │
             │ 1:N            │
    ┌────────▼─────────────────┼──────────────┐
    │      Equipo              │              │
    ├──────────────────────────┤              │
    │ id (PK)                  │              │
    │ nombre (U)               │              │
    └──────────────────────────┘              │
             ▲                                │
             │ 1:N                           │
             └────────────────────────────────┘


    ┌──────────────────────────┐
    │   SuperMatriz            │
    ├──────────────────────────┤
    │ id (PK)                  │
    │ nombre                   │
    │ descripcion              │
    │ fecha_creacion           │
    │ fecha_fin (nullable)     │
    │ archivado                │
    │ equipo_nuevo_id (FK)     │─────┐
    └──────────────────────────┘     │
             │                        │
             │ 1:N                    │
             │                    ┌───▼────────────┐
             │                    │    Equipo      │
             │                    │ (1:N relation) │
             │                    └────────────────┘
             │
    ┌────────▼──────────────────┐
    │      Matriz              │
    ├───────────────────────────┤
    │ id (PK)                   │
    │ super_matriz_id (FK)      │
    │ nombre                    │
    │ fecha_creacion            │
    │ alcances_utilizados       │
    │ dispositivo_id (FK)       │──┐
    │ modulo_id (FK, nullable)  │  │
    └────────────────────────────┘  │
             │                       │
             │ 1:N                   │
             │                  ┌────▼─────────────┐
             │                  │   Dispositivo    │
             │                  ├─────────────────┤
             │                  │ id (PK)         │
             │                  │ nombre          │
             │                  │ equipo_id (FK)  │
             │                  │ matriz_base     │
             │                  │ operativo       │
             │                  └─────────────────┘
             │
    ┌────────▼──────────────────┐
    │   MatrizRow              │
    ├───────────────────────────┤
    │ id (PK)                   │
    │ matriz_id (FK)            │
    │ numero_caso               │
    │ descripcion_del_caso      │
    │ precondiciones            │
    │ pasos_a_validar           │
    │ resultado_esperado        │
    │ resultado_actual          │
    │ estatus_caso              │
    │ tipo_validacion           │
    │ ambiente                  │
    │ fecha_creacion            │
    │ fecha_actualizacion       │
    └───────────────────────────┘

App: Accounts
=============

**Modelo: User**

Modelo personalizado basado en AbstractBaseUser.

Campos principales:

.. list-table::
   :header-rows: 1

   * - Campo
     - Tipo
     - Descripción
   * - id
     - AutoField (PK)
     - Identificador único
   * - username
     - CharField(15)
     - Nombre único de usuario
   * - nombre
     - CharField(20)
     - Nombre del usuario
   * - apellido
     - CharField(30)
     - Apellido del usuario
   * - cargo
     - CharField (choices)
     - LIDER o TESTER
   * - equipo
     - CharField (choices)
     - Equipo asignado
   * - equipo_nuevo
     - ForeignKey(Equipo)
     - Relación con tabla Equipo
   * - is_staff
     - BooleanField
     - Acceso a admin
   * - is_active
     - BooleanField
     - Usuario activo
   * - password
     - CharField
     - Contraseña hasheada
   * - last_login
     - DateTimeField
     - Último login

Opciones de cargo::

    CARGO_CHOICES = (
        ('Lider', 'LIDER'),
        ('Tester', 'TESTER')
    )

Equipos disponibles::

    EQUIPO_CHOICES = (
        ('Claro TV STB - IPTV - Roku - TATA', '...'),
        ('STV (LG,Samsung,ADR), Kepler-FireTV, STV2(...)', '...'),
        ('IPTV AOSP', '...'),
        ('WIN - WEB - Fire TV', '...'),
        ('IOS - TvOS', '...'),
        ('Android', '...'),
        ('Smart TV AAF', '...')
    )

**Modelo: Equipo**

Equipos de trabajo.

.. list-table::
   :header-rows: 1

   * - Campo
     - Tipo
     - Descripción
   * - id
     - AutoField (PK)
     - Identificador único
   * - nombre
     - CharField(100)
     - Nombre del equipo (UNIQUE)

Relaciones: 1:N con User, SuperMatriz, Dispositivo

App: Matrix
===========

**Modelo: Dispositivo**

Dispositivos de prueba.

.. list-table::
   :header-rows: 1

   * - Campo
     - Tipo
     - Descripción
   * - id
     - AutoField (PK)
     - Identificador único
   * - nombre
     - CharField(75)
     - Nombre del dispositivo
   * - equipo
     - ForeignKey(Equipo)
     - Equipo propietario
   * - matriz_base
     - CharField(75)
     - Archivo base Excel (.xlsx)
   * - operativo
     - BooleanField
     - ¿Está operativo?

Métodos importantes::

    def get_excel_url()      # Retorna URL del archivo Excel
    def get_excel_path()     # Retorna ruta física del archivo
    def excel_exists()       # Verifica si existe el archivo

**Modelo: SuperMatriz**

Agrupador de matrices (proyecto de testing).

.. list-table::
   :header-rows: 1

   * - Campo
     - Tipo
     - Descripción
   * - id
     - AutoField (PK)
     - Identificador único
   * - nombre
     - CharField(75)
     - Nombre del proyecto
   * - descripcion
     - TextField
     - Descripción
   * - fecha_creacion
     - DateTimeField
     - Fecha auto
   * - fecha_fin
     - DateField (nullable)
     - Fecha tentativa de fin
   * - equipo_nuevo
     - ForeignKey(Equipo)
     - Equipo asignado
   * - archivado
     - BooleanField
     - ¿Está archivado?

Métodos::

    def clean()              # Validación: fecha_fin >= fecha_creacion
    def archivar()           # Marca como archivado

**Modelo: Matriz**

Matriz de testing individual.

.. list-table::
   :header-rows: 1

   * - Campo
     - Tipo
     - Descripción
   * - id
     - AutoField (PK)
     - Identificador único
   * - super_matriz
     - ForeignKey(SuperMatriz)
     - Proyecto padre
   * - nombre
     - CharField(70)
     - Nombre de matriz
   * - fecha_creacion
     - DateTimeField
     - Fecha auto
   * - alcances_utilizados
     - CharField
     - Alcances de la matriz
   * - dispositivo
     - ForeignKey(Dispositivo)
     - Dispositivo de prueba
   * - modulo
     - ForeignKey(Modulo, nullable)
     - Módulo relacionado

**Modelo: MatrizRow**

Fila/caso de prueba dentro de una matriz.

.. list-table::
   :header-rows: 1

   * - Campo
     - Tipo
     - Descripción
   * - id
     - AutoField (PK)
     - Identificador único
   * - matriz
     - ForeignKey(Matriz)
     - Matriz padre
   * - numero_caso
     - IntegerField
     - Número del caso
   * - descripcion_del_caso
     - TextField
     - Descripción del caso
   * - precondiciones
     - TextField
     - Precondiciones
   * - pasos_a_validar
     - TextField
     - Pasos a ejecutar
   * - resultado_esperado
     - TextField
     - Resultado esperado
   * - resultado_actual
     - TextField (nullable)
     - Resultado obtenido
   * - estatus_caso
     - CharField (choices)
     - PASS, FAIL, PENDIENTE, NO APLICA
   * - tipo_validacion
     - CharField
     - Tipo de validación
   * - ambiente
     - CharField
     - Ambiente de prueba
   * - fecha_creacion
     - DateTimeField
     - Fecha auto
   * - fecha_actualizacion
     - DateTimeField
     - Última actualización

Estados disponibles::

    ESTATUS_CHOICES = (
        ('PASS', 'PASS'),
        ('FAIL', 'FAIL'),
        ('PENDIENTE', 'PENDIENTE'),
        ('NO APLICA', 'NO APLICA')
    )

Índices de Base de Datos
========================

**Principales**::

    - (matriz_id, numero_caso) - Búsqueda rápida de casos
    - (matriz_id, estatus_caso) - Filtrado por estado
    - (super_matriz_id, archivado) - Matrices activas
    - (user_id, cargo) - Búsqueda de usuarios por rol
    - (dispositivo_id, operativo) - Dispositivos operativos

Relaciones y Restricciones
===========================

**User → Equipo**
- 1 Usuario puede pertenecer a 1 Equipo
- Al eliminar Equipo: SET_NULL en usuario

**Equipo → Dispositivo**
- 1 Equipo tiene N Dispositivos
- Al eliminar Equipo: CASCADE elimina dispositivos

**Equipo → SuperMatriz**
- 1 Equipo tiene N SuperMatrices
- Al eliminar Equipo: CASCADE elimina matrices

**SuperMatriz → Matriz**
- 1 SuperMatriz tiene N Matrices
- Al eliminar SuperMatriz: CASCADE elimina matrices

**Matriz → MatrizRow**
- 1 Matriz tiene N Filas
- Al eliminar Matriz: CASCADE elimina filas

**Dispositivo → Matriz**
- 1 Dispositivo puede tener N Matrices
- Al eliminar Dispositivo: SET_NULL en matriz

Migraciones
===========

Crear nuevas migraciones después de cambiar modelos::

    python manage.py makemigrations

Aplicar migraciones::

    python manage.py migrate

Ver estado::

    python manage.py showmigrations

Revertir migración::

    python manage.py migrate app_name migration_number

Consultas SQL Útiles
====================

**Obtener todas las matrices de un equipo**::

    SELECT * FROM matrix_matriz m
    JOIN matrix_supermatriz sm ON m.super_matriz_id = sm.id
    WHERE sm.equipo_nuevo_id = 1

**Contar casos PASS y FAIL por matriz**::

    SELECT matriz_id, estatus_caso, COUNT(*) 
    FROM matrix_matrizrow
    GROUP BY matriz_id, estatus_caso

**Usuarios por equipo**::

    SELECT u.username, e.nombre
    FROM accounts_user u
    JOIN accounts_equipo e ON u.equipo_nuevo_id = e.id
    ORDER BY e.nombre

**Matrices no archivadas**::

    SELECT * FROM matrix_supermatriz 
    WHERE archivado = FALSE 
    ORDER BY fecha_creacion DESC

Optimizaciones de Consultas
============================

En las vistas, usar::

    # En lugar de:
    matrices = Matriz.objects.all()
    
    # Usar:
    matrices = Matriz.objects.select_related('super_matriz', 'dispositivo').prefetch_related('filas')

Esto reduce el número de queries a la DB (N+1 problem).
