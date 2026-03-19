# Informe detallado: integración Gherkin (.feature) y edición

Resumen de todos los cambios a nivel arquitectura, base de datos, librerías, decisiones tomadas, ventajas y desventajas.

---

## 1. Objetivo general

- Tratar los archivos **Gherkin (.feature)** como fuente de verdad de casos de prueba.
- Permitir **varios archivos .feature por matriz**.
- **Editar** el contenido de los .feature desde la aplicación (sin edición colaborativa en tiempo real).
- Mantener **sincronización** entre el contenido del archivo y los casos de prueba en la matriz (estados, fases, escenarios).

---

## 2. Arquitectura

### 2.1 Flujo de datos

```
[Archivo .feature en disco]  ←→  [FeatureFile + FeatureScenario en BD]
            ↑                                    ↓
            |                         [CasoDePrueba por escenario]
            |                                    ↓
      [Editor Monaco]                    [Vista detalle_matriz]
            ↓
      [POST guardar] → validar ruta → escribir disco → sync_scenarios_from_featurefile
```

- **Origen de verdad:** el contenido del archivo en `MEDIA_ROOT/features/`.
- **BD:** solo metadata (ruta, nombre, SHA256) y estado de escenarios; el texto Gherkin no se guarda en BD.
- **Sincronización:** al subir o guardar un .feature se re-parsea el archivo y se crean/actualizan `FeatureScenario` y `CasoDePrueba`; se conservan estados/observaciones de escenarios que siguen existiendo.

### 2.2 Reglas de negocio

| Regla | Decisión |
|-------|----------|
| Varios archivos en una subida | Todos pertenecen a **una sola matriz** (nueva o existente). Para varias matrices, varias subidas. |
| Fase en CasoDePrueba | Nombre del **Feature** (línea `Feature: ...`). Truncado a 50 caracteres. |
| Caso de prueba | Línea completa del **Scenario** o **Scenario Outline**. |
| Nuevo Scenario en el editor | Al guardar, el sync crea el **CasoDePrueba** correspondiente en la matriz. |
| Edición en tiempo real | **No** implementada; solo edición local + guardado HTTP para simplificar. |

### 2.3 Componentes principales

- **Vistas HTTP:** subir feature(s), vista previa (uno / todos), editor, guardar, gestionar (listar/eliminar).
- **Parser Gherkin:** en `views.py`, función que extrae nombre del Feature y lista de escenarios (nombre, línea, tags, pasos).
- **Sync:** `sync_scenarios_from_featurefile()` — lee archivo, recalcula SHA256, actualiza FeatureScenario y CasoDePrueba.
- **Editor:** una sola página con Monaco (CDN); guardado por POST a `/feature/<id>/guardar/`.

### 2.4 Seguridad

- Ruta del archivo validada contra `FEATURES_ROOT` (no salir del directorio de features).
- Solo usuarios autenticados (`@login_required`) para editor, guardar, subir y gestionar.
- Guardado: comprobación de ruta antes de escribir en disco.

---

## 3. Base de datos

### 3.1 Modelos nuevos o modificados

| Modelo / campo | Tipo | Descripción |
|----------------|------|-------------|
| **FeatureFile** | Modelo nuevo | Archivo .feature: FK a SuperMatriz, Dispositivo, Matriz; FileField (storage en FEATURES_ROOT); nombre_archivo, ruta_relativa, sha256; unique_together (matriz, ruta_relativa). |
| **FeatureScenario** | Modelo nuevo | Escenario parseado: FK a FeatureFile; stable_id, nombre, linea, tags, estado, observaciones; unique_together (feature_file, stable_id). |
| **CasoDePrueba.scenario_stable_id** | CharField(255), opcional | Identificador estable para vincular caso con escenario Gherkin; formato `{feature_file_id}-{slug}-{linea}` para soportar varios .feature por matriz. |

### 3.2 Relaciones

- **FeatureFile** → SuperMatriz (N:1), Dispositivo (N:1), **Matriz (N:1)**. Una matriz puede tener varios FeatureFile.
- **FeatureScenario** → FeatureFile (N:1).
- **CasoDePrueba** → Matriz (N:1); `scenario_stable_id` indica el escenario del .feature del que proviene (si aplica).

### 3.3 Migraciones relevantes

- **0023:** Creación de FeatureFile y FeatureScenario (unique_together en super_matriz + ruta_relativa inicial).
- **0024:** Añade `CasoDePrueba.scenario_stable_id` y `FeatureFile.matriz` (en origen OneToOne).
- **0025** (si se aplicó): Cambio de FeatureFile.matriz de OneToOne a **ForeignKey** (varios .feature por matriz) y unique_together (matriz, ruta_relativa); eliminación de la restricción UNIQUE sobre `matriz_id`.

### 3.4 Restricciones y convenciones

- `CasoDePrueba.fase` tiene `max_length=50`; en el sync se usa siempre `fase_val = (feature_name or '')[:50]` para evitar `StringDataRightTruncation`.
- `scenario_stable_id` incluye `feature_file.id` para no colisionar entre archivos de la misma matriz.

---

## 4. Librerías y tecnologías

### 4.1 Usadas en esta funcionalidad

| Recurso | Uso | Notas |
|---------|-----|--------|
| **Monaco Editor** | Editor de texto en el navegador para .feature | CDN (sin build); lenguaje “gherkin” definido con Monarch (keywords, comentarios, strings, tags). |
| **Django** | Vistas, modelos, formularios, validación de ruta | Sin cambios de versión. |
| **FileSystemStorage** | Almacenamiento de .feature en disco | Ruta configurada con `FEATURES_ROOT`. |
| **hashlib (SHA256)** | Checksum del archivo .feature | Recalculado al guardar; solo metadata en BD. |

### 4.2 No usadas (simplificación)

- **Django Channels / WebSocket** para el editor de .feature: se eliminó la edición colaborativa en tiempo real.
- **Redis** para locks de edición: se eliminó el módulo `feature_lock.py` y la lógica de lock.
- **Yjs / OT** u otras librerías de colaboración: no se usan; sincronización simple vía “guardar y re-parsear”.

### 4.3 Existentes en el proyecto (sin cambios para Gherkin)

- **Channels + Redis:** siguen usándose para la matriz (estados/notas en tiempo real en `detalle_matriz`).
- **PostgreSQL:** BD del proyecto.
- **Bootstrap 5:** UI de las vistas (subir, gestionar, detalle_matriz, etc.).

---

## 5. Decisiones y motivos

| Decisión | Motivo |
|----------|--------|
| Varios .feature por matriz (FK en lugar de OneToOne) | Permitir una matriz con múltiples archivos Gherkin (p. ej. por módulo o dispositivo). |
| Varios archivos en una subida → una sola matriz | Evitar crear muchas matrices de golpe; una subida = una matriz; matrices adicionales con subidas nuevas. |
| Contenido .feature solo en disco | Evitar duplicar texto grande en BD; el archivo es la fuente de verdad. |
| Editor sin WebSocket | Reducir complejidad (Channels, Redis, locks) y evitar problemas de conexión; edición local + guardado HTTP suficiente. |
| Monaco desde CDN | No introducir tooling de build; carga directa en el navegador. |
| Fase = nombre del Feature, Caso = Scenario/Scenario Outline | Alinear con Gherkin: Feature como agrupación (fase), Scenario como caso de prueba. |
| Truncar fase a 50 caracteres | Respetar `CasoDePrueba.fase` max_length=50 sin cambiar el modelo. |
| Validar ruta contra FEATURES_ROOT | Evitar escritura fuera del directorio de features (path traversal). |
| Reducir polling en detalle_matriz (60 s) | Menos peticiones innecesarias (GET página completa y num-fallos) manteniendo actualizaciones útiles. |

---

## 6. Ventajas

- **Fuente única de verdad:** el .feature en disco; la BD solo refleja metadata y estados.
- **Sincronización clara:** un solo flujo (subir o guardar → sync) para actualizar escenarios y casos de prueba.
- **Varios .feature por matriz:** mayor flexibilidad (múltiples archivos por matriz).
- **Editor usable:** Monaco con resaltado Gherkin y guardado explícito; mensajes claros al guardar.
- **Sin dependencias pesadas para el editor:** no requiere Channels/Redis para editar .feature.
- **Seguridad:** validación de ruta y autenticación en todas las acciones.
- **Gestión centralizada:** listado, filtro por super matriz y eliminación (archivo + BD) desde “Archivos .feature”.
- **Nuevos Scenario en el editor:** al guardar, se crean automáticamente como casos de prueba en la matriz.

---

## 7. Desventajas y limitaciones

- **Sin edición colaborativa:** dos usuarios no ven cambios en vivo; el último que guarda sobrescribe.
- **Fase truncada a 50 caracteres:** nombres de Feature muy largos se cortan en la matriz (solución actual sin migración).
- **Sincronización “todo o nada”:** cada guardado re-parsea todo el archivo; no hay merge fino de cambios.
- **Monaco en CDN:** depende de disponibilidad del CDN; no se puede usar totalmente offline sin cache.
- **Polling en detalle_matriz:** aunque reducido (60 s), sigue existiendo para tabla y num-fallos; en entornos muy sensibles a carga se podría afinar más o depender solo del WebSocket.

---

## 8. Archivos y rutas principales

| Ruta / archivo | Función |
|----------------|--------|
| `app/matrix/models.py` | FeatureFile, FeatureScenario; CasoDePrueba.scenario_stable_id; feature_storage. |
| `app/matrix/views.py` | Parser Gherkin, sync_scenarios_from_featurefile, subir_feature, editor_feature, guardar_feature_file, vista_previa_*, gestionar_features, eliminar_feature_file; _feature_file_path_safe. |
| `app/matrix/forms.py` | FeatureUploadForm (super_matriz, dispositivo; archivos validados en vista). |
| `app/matrix/urls.py` | Rutas para feature (ver, editar, guardar, gestionar, eliminar). |
| `templates/excel_files/editor_feature.html` | Página del editor (Monaco + guardar + mensajes). |
| `templates/excel_files/subir_feature.html` | Subida múltiple de .feature. |
| `templates/excel_files/gestionar_features.html` | Listado y eliminación de archivos .feature. |
| `templates/excel_files/vista_previa_gherkin.html` | Vista previa de un .feature. |
| `templates/excel_files/vista_previa_gherkin_todos.html` | Vista previa de todos los .feature de una matriz (acordeón). |
| `main_website/settings/base.py` | FEATURES_ROOT. |
| `media/features/` (o MEDIA_ROOT/features) | Directorio físico de los .feature. |

---

## 9. Resumen ejecutivo

Se integraron los archivos Gherkin (.feature) como fuente de verdad de casos de prueba: se almacenan en disco, la BD guarda metadata y estado de escenarios, y la edición se hace con Monaco y guardado HTTP. Se permiten varios .feature por matriz y varias subidas en una sola operación hacia una única matriz. Se descartó la edición colaborativa en tiempo real para simplificar (sin WebSocket ni Redis para el editor). La sincronización entre archivo y casos de prueba es automática al subir o guardar, y los nuevos Scenario/Scenario Outline pasan a ser casos de prueba en la matriz. Las principales limitaciones son la ausencia de colaboración en vivo y el truncado del nombre del Feature a 50 caracteres en la fase del caso de prueba.
