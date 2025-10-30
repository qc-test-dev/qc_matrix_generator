# 📚 Documentación Sphinx - QC Matrix Generator

## ✅ Archivos Incluidos

He generado **documentación profesional completa** en formato **Sphinx (.rst)**:

### Archivos principales:
- ✅ `index.rst` - Portada y tabla de contenidos
- ✅ `inicio-rapido.rst` - Guía de instalación (local y Docker)
- ✅ `arquitectura.rst` - Descripción de arquitectura y flujos
- ✅ `modelos-bbdd.rst` - Modelos Django y diagrama ER completo
- ✅ `api-rest.rst` - Documentación de todos los endpoints REST
- ✅ `docker-redis.rst` - Configuración Docker, Redis, comandos
- ✅ `desarrollo.rst` - Guía para desarrolladores
- ✅ `conf.py` - Configuración Sphinx profesional
- ✅ `.readthedocs.yaml` - Configuración para Read the Docs
- ✅ `requirements-docs.txt` - Dependencias de documentación

---

## 🚀 Pasos para Instalar

### 1. Copiar archivos al proyecto

Descarga TODOS los archivos `.rst` y cópialos a tu proyecto:

```bash
# En tu repo local
mkdir -p docs/source

# Copiar archivos descargados a:
# - .readthedocs.yaml → raíz del proyecto
# - conf.py → docs/source/conf.py
# - *.rst → docs/source/
# - requirements-docs.txt → docs/requirements.txt
```

**Estructura esperada:**

```
qc_matrix_generator/
├── .readthedocs.yaml              ← Descargado
├── docs/
│   ├── requirements.txt            ← requirements-docs.txt renombrado
│   └── source/
│       ├── conf.py                 ← Descargado
│       ├── index.rst               ← Descargado
│       ├── inicio-rapido.rst       ← Descargado
│       ├── arquitectura.rst        ← Descargado
│       ├── modelos-bbdd.rst        ← Descargado
│       ├── api-rest.rst            ← Descargado
│       ├── docker-redis.rst        ← Descargado
│       └── desarrollo.rst          ← Descargado
├── manage.py
├── requirements.txt
└── ...
```

### 2. Agregar a Git

```bash
cd qc_matrix_generator
git add .readthedocs.yaml docs/
git commit -m "docs: agregar documentación Sphinx completa"
git push origin dev
```

### 3. Configurar en Read the Docs

1. Ve a https://readthedocs.org/
2. Haz login con tu cuenta GitHub
3. Click en **"+ Import a Project"**
4. Busca `qc_matrix_generator`
5. Click "Create"
6. Read the Docs detectará automáticamente `.readthedocs.yaml`
7. ¡Automáticamente comenzará a construir la documentación!

---

## 🔍 Verificar que funcione

### Localmente:

```bash
# Instalar Sphinx
pip install -r docs/requirements.txt

# Construir documentación
cd docs
make html

# Abrir en navegador
open source/_build/html/index.html          # macOS
xdg-open source/_build/html/index.html      # Linux
start source/_build/html/index.html         # Windows
```

### En Read the Docs:

- URL: `https://qc-matrix-generator.readthedocs.io/`
- (Cambiar "qc-matrix-generator" por el nombre real si es diferente)

---

## 📖 Qué contiene la documentación

### 1. **Inicio Rápido**
   - Instalación local sin Docker
   - Instalación con Docker Compose
   - Pasos iniciales después de instalar

### 2. **Arquitectura**
   - Descripción general del sistema
   - Stack tecnológico (Django, PostgreSQL, Redis, etc)
   - Estructura de directorios
   - Flujo de datos principales
   - Diagramas ASCII de componentes

### 3. **Modelos y BBDD**
   - Diagrama Entidad-Relación (ER) completo
   - Descripción de cada modelo (User, Equipo, SuperMatriz, Matriz, MatrizRow, Dispositivo)
   - Campos, tipos, relaciones
   - Migraciones
   - Índices de base de datos
   - Consultas SQL útiles
   - Optimizaciones

### 4. **API REST**
   - Autenticación (Token, Session)
   - Endpoints de login/logout
   - CRUD completo de SuperMatriz
   - CRUD completo de Matriz
   - CRUD de MatrizRow (casos)
   - Filtros y búsqueda
   - Estadísticas y reportes
   - Errores HTTP comunes
   - Ejemplos con cURL
   - WebSockets para chat

### 5. **Docker y Redis**
   - Servicios en docker-compose.yml (PostgreSQL, Redis, Django, Nginx)
   - Comandos docker-compose útiles
   - Variables de entorno
   - Análisis del Dockerfile
   - Volúmenes y data persistence
   - Health checks
   - Configuración de Redis en Django
   - Comandos Redis útiles
   - Troubleshooting
   - Performance tuning
   - Backup y restore
   - Escalado en producción

### 6. **Desarrollo**
   - Setup del entorno local
   - Workflow de Git (ramas, commits, PR)
   - Creación de modelos y migraciones
   - Crear nuevas apps
   - APIs con Django REST Framework
   - WebSockets (Consumers)
   - Testing (unitarios, coverage)
   - Debugging (shell, logs, debug toolbar)
   - Estándares de código (PEP 8, docstrings)
   - Recursos útiles

---

## 🔧 Personalización

### Cambiar tema

En `docs/source/conf.py`::

    html_theme = 'sphinx_rtd_theme'  # Cambiar por otro tema

Temas disponibles:
- `sphinx_rtd_theme` (actual - recomendado)
- `alabaster`
- `classic`
- `pydata_sphinx_theme`

### Agregar logo

```python
# En conf.py
html_logo = '_static/logo.png'
html_favicon = '_static/favicon.ico'
```

### Agregar más secciones

1. Crear archivo `.rst` en `docs/source/`
2. Agregarlo a `index.rst` en `toctree`

Ejemplo:
```rst
.. toctree::
   :maxdepth: 2

   mi-nueva-seccion
```

---

## 📝 Formato RST (reStructuredText)

Referencia rápida:

```rst
# Título principal
###############

## Subtítulo
============

### Sub-subtítulo
-----------------

Párrafo normal.

**Negrita** e *itálica*

- Punto 1
- Punto 2
- Punto 3

1. Numerado 1
2. Numerado 2

::

    Código preformateado
    Sin colores

.. code-block:: python

    # Código con colores
    def mi_funcion():
        pass

.. code-block:: bash

    $ comando

Link: `Texto <https://url.com>`_

[Referencia]: https://url.com
Ver [Referencia]

.. note::
    Nota importante

.. warning::
    Advertencia

.. image:: /path/to/image.png
    :width: 400

.. table:: Tabla ejemplo

    ====== ======
    Col1   Col2
    ====== ======
    Val1   Val2
    ====== ======
```

---

## ❓ Troubleshooting

**Error: "config file not found"**

- Asegúrate que `.readthedocs.yaml` está en la raíz del repo
- Verifica que `docs/source/conf.py` existe

**Error: "sphinx_rtd_theme not found"**

- Verifica que `docs/requirements.txt` tiene `sphinx-rtd-theme`
- Verifica que el archivo se llama `docs/requirements.txt` (no `requirements-docs.txt`)

**Error en Read the Docs: "Build failed"**

- Ver logs: Click en "Builds" → "Latest" → Ver logs detallados
- Buscar líneas rojas que indiquen el problema
- Común: archivos `.rst` con sintaxis incorrecta

**¿Por qué no se actualiza?**

- Read the Docs reconstruye automáticamente cuando haces push
- Puede tardar 1-2 minutos
- Puedes forzar rebuild en Read the Docs → "Build" → "Rebuild"

---

## 📚 Recursos

- **Sphinx Documentation**: https://www.sphinx-doc.org/
- **Read the Docs**: https://docs.readthedocs.io/
- **reStructuredText Primer**: https://www.sphinx-doc.org/en/master/usage/restructuredtext/

---

## ✨ Próximos Pasos

Una vez esté funcionando:

1. **Leer la documentación** para familiarizarse con el proyecto
2. **Actualizar secciones** según cambios en el código
3. **Agregar secciones nuevas** según necesidad
4. **Comentarios en PR**: "Lee la sección X en la documentación"

---

**¡Listo! Ya tienes documentación profesional que se actualiza automáticamente cada vez que haces push a GitHub.** 🚀

Si hay dudas, pregunta. 👍
