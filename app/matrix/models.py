# models.py
from django.db import models
from ..accounts.models import Equipo
from django.core.exceptions import ValidationError
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils import timezone
from app.accounts.utils import procesar_excel_matriz
import os
import pandas as pd
import hashlib
from django.utils.text import slugify
#from io import BytesIO
# Storage personalizado ara archivos Excel
excel_storage = FileSystemStorage(
    location=os.path.join(settings.MEDIA_ROOT, 'excel'),
    base_url=f'{settings.MEDIA_URL}excel/'
)

class Dispositivo(models.Model):
    nombre = models.CharField(max_length=75)
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='dispositivos')
    matriz_base = models.CharField(max_length=75, blank=True, null=True)
    
    operativo = models.BooleanField(
        default=False,
        blank=True,
        null=True,
        verbose_name="Operativo"
    )
    
    archivo_excel = models.FileField(
        upload_to='',  # Vacío, lo manejaremos manualmente
        storage=excel_storage,
        verbose_name="Archivo Excel",
        blank=True,
        null=True
    )
    
    created_at = models.DateTimeField(auto_now_add=False, default=timezone.now)
    updated_at = models.DateTimeField(auto_now=False, default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.nombre}"
    
    def generar_nombre_unico(self, nombre_original):
        """
        Genera un nombre único para el archivo.
        Si ya existe en el mismo equipo, añade _1, _2, etc.
        """
        # Obtener solo el nombre del archivo (sin ruta)
        nombre_base = os.path.basename(nombre_original)
        
        # Separar nombre y extensión
        if '.' in nombre_base:
            nombre, extension = nombre_base.rsplit('.', 1)
            extension = '.' + extension
        else:
            nombre = nombre_base
            extension = ''
        
        # Verificar nombres existentes en el MISMO equipo
        nombres_existentes = list(Dispositivo.objects.filter(
            equipo=self.equipo
        ).exclude(pk=self.pk).values_list('matriz_base', flat=True))
        
        # Si el nombre original no existe, usarlo
        if nombre_base not in nombres_existentes:
            return nombre_base
        
        # Si existe, buscar el siguiente número disponible
        contador = 1
        while True:
            nombre_propuesto = f"{nombre}_{contador}{extension}"
            
            if nombre_propuesto not in nombres_existentes:
                return nombre_propuesto
            
            contador += 1
            
            # Prevención de bucle infinito
            if contador > 100:
                # Usar timestamp como fallback
                import time
                timestamp = int(time.time())
                return f"{nombre}_{timestamp}{extension}"
    
    def save(self, *args, **kwargs):
        """
        IMPORTANTE: Este método NO procesa el Excel.
        El procesamiento se hace en el formulario.
        """
        # Actualizar timestamps
        if not self.pk:  # Si es nuevo
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    def get_excel_url(self):
        """Retorna la URL para descargar el archivo Excel"""
        if self.archivo_excel and self.archivo_excel.name:
            return self.archivo_excel.url
        return None
    
    def get_excel_path(self):
        """Retorna la ruta física del archivo Excel"""
        if self.archivo_excel and self.archivo_excel.name:
            return self.archivo_excel.path
        return None
    
    def excel_exists(self):
        """Verifica si el archivo Excel existe"""
        path = self.get_excel_path()
        return path and os.path.exists(path)
    
    def get_filename(self):
        """Retorna solo el nombre del archivo"""
        if self.matriz_base:
            return self.matriz_base
        elif self.archivo_excel and self.archivo_excel.name:
            return os.path.basename(self.archivo_excel.name)
        return ""
    
    def delete(self, *args, **kwargs):
        """Eliminar el archivo físico al eliminar el dispositivo"""
        if self.archivo_excel:
            # Eliminar el archivo físico
            self.archivo_excel.delete(save=False)
        
        # Eliminar el objeto de la base de datos
        super().delete(*args, **kwargs)


# Storage para archivos Gherkin (.feature)
feature_storage = FileSystemStorage(
    location=getattr(settings, "FEATURES_ROOT", os.path.join(settings.MEDIA_ROOT, "features")),
    base_url=f'{settings.MEDIA_URL}features/'
)


class FeatureFile(models.Model):
    """
    Archivo .feature en filesystem.
    La BD solo guarda metadata + referencia al archivo.
    """
    super_matriz = models.ForeignKey(
        'SuperMatriz',
        on_delete=models.CASCADE,
        related_name='feature_files'
    )
    dispositivo = models.ForeignKey(
        Dispositivo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='feature_files'
    )

    # Archivo físico (solo ruta en BD, contenido en disco)
    archivo_feature = models.FileField(
        upload_to='',
        storage=feature_storage,
        verbose_name="Archivo Gherkin (.feature)"
    )

    # Metadata
    nombre_archivo = models.CharField(max_length=255)        # ej: login.feature
    ruta_relativa = models.CharField(max_length=500)         # ej: features/login.feature
    sha256 = models.CharField(max_length=64, blank=True)     # checksum del contenido

    # CSV opcional para expandir Scenario Outline: una fila → un caso de prueba
    archivo_csv = models.FileField(
        upload_to='csv/',
        storage=feature_storage,
        verbose_name="CSV de Examples (opcional)",
        blank=True,
        null=True,
    )

    # Matriz lógica asociada (una matriz puede tener varios .feature)
    matriz = models.ForeignKey(
        'Matriz',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='feature_files'
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-creado_en']
        unique_together = ('matriz', 'ruta_relativa')

    def __str__(self):
        return f"{self.super_matriz} :: {self.nombre_archivo}"

    def get_feature_url(self):
        if self.archivo_feature and self.archivo_feature.name:
            return self.archivo_feature.url
        return None

    def get_feature_path(self):
        if self.archivo_feature and self.archivo_feature.name:
            return self.archivo_feature.path
        return None

    def get_csv_path(self):
        """Ruta absoluta del CSV vinculado (para expandir Scenario Outline)."""
        if self.archivo_csv and self.archivo_csv.name:
            return self.archivo_csv.path
        return None

    def has_csv(self):
        path = self.get_csv_path()
        return path and os.path.exists(path)

    def recalcular_sha256(self):
        """
        Lee el archivo desde disco y recalcula el SHA256.
        """
        path = self.get_feature_path()
        if not path or not os.path.exists(path):
            self.sha256 = ""
            return

        hasher = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        self.sha256 = hasher.hexdigest()

    def save(self, *args, **kwargs):
        # Mantener nombre y ruta relativa coherentes
        if self.archivo_feature and self.archivo_feature.name:
            self.nombre_archivo = os.path.basename(self.archivo_feature.name)
            self.ruta_relativa = f"features/{self.nombre_archivo}"
        super().save(*args, **kwargs)


class FeatureScenario(models.Model):
    """
    Escenario parseado desde un .feature.
    El texto Gherkin vive en el archivo; aquí solo estado/observaciones
    y datos mínimos para mostrarlo y emparejarlo entre versiones.
    """
    feature_file = models.ForeignKey(
        FeatureFile,
        on_delete=models.CASCADE,
        related_name='scenarios'
    )

    # Identificador estable derivado del escenario, para conservar estado
    stable_id = models.CharField(max_length=255)

    # Datos del escenario que vienen del .feature (no se editan desde UI)
    nombre = models.CharField(max_length=500)       # "Scenario: login success"
    linea = models.IntegerField()                   # línea donde empieza el Scenario
    tags = models.CharField(max_length=500, blank=True)  # "@smoke @regression"

    # Estado y observaciones editables desde la UI
    ESTADO_CHOICES = [
        ('por_ejecutar', 'Por ejecutar'),
        ('funciona', 'Funciona'),
        ('falla_nueva', 'Falla nueva'),
        ('falla_persistente', 'Falla persistente'),
        ('bloqueado', 'Bloqueado'),
        ('n_a', 'N/A'),
    ]
    estado = models.CharField(
        max_length=30,
        choices=ESTADO_CHOICES,
        default='por_ejecutar',
    )
    observaciones = models.TextField(blank=True, null=True, max_length=500)

    sincronizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('feature_file', 'stable_id')
        ordering = ['linea']

    def __str__(self):
        return f"{self.feature_file.nombre_archivo} :: {self.nombre}"

    @staticmethod
    def build_stable_id(nombre_escenario: str, linea: int) -> str:
        """
        Helper para generar un ID estable a partir del nombre + línea.
        Esto se usa en el proceso de parseo para poder mantener el estado
        aunque se reescriba el .feature.
        """
        base = f"{slugify(nombre_escenario)}-{linea}"
        return base[:250]


class SuperMatriz(models.Model):
    nombre = models.CharField(max_length=75)
    descripcion = models.TextField(blank=True, null=True, max_length=200)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    equipo = models.CharField('Equipo', max_length=150, blank=True, null=True)  # Campo antiguo (temporal)
    equipo_nuevo = models.ForeignKey(
        Equipo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supermatrices'
    )
    fecha_fin = models.DateField("Fecha Tentativa", null=True, blank=True)
    archivado = models.BooleanField(default=False, blank=True, null=True)  # Nuevo campo
    
    def __str__(self):
        return self.nombre
    
    def clean(self):
        super().clean()
        # Validación segura
        if self.fecha_fin and self.fecha_creacion:
            if self.fecha_fin < self.fecha_creacion.date():
                raise ValidationError({
                    'fecha_fin': "La fecha fin no puede ser anterior a la fecha de creación."
                })
    
    def archivar(self):
        """Función para archivar la matriz"""
        self.archivado = True
        self.save()
class Matriz(models.Model):
    super_matriz = models.ForeignKey(
        'SuperMatriz',
        on_delete=models.CASCADE,
        related_name='matrices'
    )
    nombre = models.CharField(max_length=70)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    alcances_utilizados = models.CharField(max_length=100, blank=True, null=True)
    dispositivo = models.ForeignKey(
        'Dispositivo',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='matrices'
    )
    testers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='matrices_asignadas',
        blank=True
    )

    def __str__(self):
        return self.nombre
class CasoDePrueba(models.Model):
    CRITICIDAD_CHOICES = [
        ('Bloqueante', 'Bloqueante'),
        ('Crítico', 'Crítico'),
    ]
    matriz = models.ForeignKey(Matriz, on_delete=models.CASCADE, related_name='casos')
    alcance = models.CharField(max_length=5)
    fase = models.CharField(max_length=50)
    caso_de_prueba = models.TextField()
    estado = models.CharField(max_length=50, default="Por ejecutar")
    criticidad = models.CharField(max_length=15, choices=CRITICIDAD_CHOICES)
    nota = models.TextField(blank=True, null=True,max_length=150)
    tester = models.TextField(blank=True, null=True)
    tester_asignado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='casos_asignados'
    )
    pais = models.CharField(max_length=50, blank=True, null=True)
    etiqueta=models.CharField(max_length=50, blank=True, null=True)
    tipo_usuario=models.CharField(max_length=70, blank=True, null=True)
    pasos=models.CharField(max_length=700,blank=True, null=True)
    # Identificador estable opcional para vincular con escenarios Gherkin (.feature)
    scenario_stable_id = models.CharField(max_length=255, blank=True, null=True)
    # Datos de la fila del CSV cuando el caso viene de un Scenario Outline expandido (JSON)
    datos_examples = models.JSONField(blank=True, null=True)
    def __str__(self):
        return f"{self.fase} - {self.caso_de_prueba[:30]}..."
class Validate(models.Model):
    super_matriz = models.ForeignKey(SuperMatriz, on_delete=models.CASCADE, related_name='validates')
    matriz = models.ForeignKey(Matriz, on_delete=models.CASCADE, related_name='validates', null=True, blank=True)
    tester = models.CharField(max_length=255, null=True, blank=True)
    ticket = models.CharField(max_length=100, null=True, blank=True)
    descripcion = models.TextField(null=True, blank=True)
    prioridad = models.CharField(max_length=50, null=True, blank=True)
    estado = models.CharField(max_length=50, null=True, blank=True)
    def __str__(self):
        ticket_url = f"https://dlatvarg.atlassian.net/browse/{self.ticket}" if self.ticket else "Sin Ticket"
        return f"{self.tester} — <a href='{ticket_url}' target='_blank'>{ticket_url}</a>"
class TicketPorLevantar(models.Model):
    PRIORIDAD_CHOICES = [
        ('bloqueante', 'Bloqueante'),
        ('critico', 'Critico'),
    ]
    super_matriz = models.ForeignKey(SuperMatriz, on_delete=models.CASCADE, related_name='tickets_por_levantar')
    tester = models.CharField(max_length=100, blank=True, null=True)
    tester_asignado = models.ForeignKey(
        settings.AUTH_USER_MODEL,  
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets_asignados'
    )
    ticket_SCT = models.CharField(max_length=10, blank=True, null=True)
    BRF = models.CharField(max_length=30, blank=True, null=True)
    Region = models.CharField(max_length=100)
    desc = models.TextField(max_length=70)
    prioridad = models.CharField(max_length=50, choices=PRIORIDAD_CHOICES)  
    nota = models.TextField(max_length=70)
    url = models.URLField(null=True, blank=True)

    def __str__(self):
        return f"{self.tester_asignado or self.tester} - {self.ticket_SCT}"
class DetallesValidate(models.Model):
    super_matriz = models.OneToOneField(SuperMatriz, on_delete=models.CASCADE, related_name='detalles_validate')   
    filtro_RN = models.CharField(max_length=100, blank=True, null=True)
    comentario_RN = models.TextField(blank=True, null=True)
    def __str__(self):
        return f"Detalles de {self.super_matriz.nombre}"
# def procesar_excel_matriz(archivo_excel):
#     """
#     Procesa el archivo Excel según los requisitos:
#     - Busca los headers en CUALQUIER FILA del Excel
#     - EXTRAE DATOS MANUALMENTE usando la estructura correcta
#     - Descarta filas anteriores a los headers encontrados
#     - Procesa solo los datos después de los headers
    
#     Retorna el archivo procesado (BytesIO)
#     """
#     try:
#         # ============================================
#         # 1. LEER EXCEL CRUDO
#         # ============================================
#         print(f"\n🔄 LEYENDO EXCEL CRUDO...")
        
#         # Leer el Excel COMPLETO sin headers
#         df_raw = pd.read_excel(archivo_excel, engine='openpyxl', header=None)
#         print(f"📄 Excel crudo: {df_raw.shape[0]} filas, {df_raw.shape[1]} columnas")
        
#         # Mostrar estructura real del Excel
#         print(f"\n🔍 ESTRUCTURA DEL EXCEL (primeras 10 filas):")
#         for i in range(min(10, len(df_raw))):
#             row_values = []
#             for cell in df_raw.iloc[i]:
#                 if pd.isna(cell):
#                     row_values.append("")
#                 else:
#                     row_values.append(str(cell).strip())
#             print(f"Fila {i}: {row_values}")
        
#         # ============================================
#         # 2. BUSCAR LA FILA CON LOS HEADERS REALES
#         # ============================================
#         print(f"\n🔍 BUSCANDO HEADERS REALES...")
        
#         # Los headers que realmente buscamos
#         target_headers = [
#             'alcance de evaluacion',
#             'funcionalidad',
#             'descripcion',
#             'criticidad',
#             'estado',
#             'otros'
#         ]
        
#         # También aceptar variantes
#         header_variants = {
#             'alcance de evaluacion': ['alcance de evaluación', 'alcance'],
#             'funcionalidad': ['fase', 'funcionalidad o fase'],
#             'descripcion': ['descripción', 'caso de prueba', 'caso prueba'],
#             'criticidad': ['prioridad'],
#             'estado': ['status'],
#             'otros': ['comentarios', 'comentarios y datos de prueba']
#         }
        
#         header_row_idx = None
#         header_positions = {}  # {header_name: column_index}
        
#         for row_idx in range(min(50, len(df_raw))):
#             row = df_raw.iloc[row_idx]
#             found_headers = {}
            
#             # Buscar cada header en esta fila
#             for col_idx, cell in enumerate(row):
#                 if pd.isna(cell):
#                     continue
                    
#                 cell_str = str(cell).strip().lower()
                
#                 # Buscar cada header target
#                 for target in target_headers:
#                     target_lower = target.lower()
                    
#                     # Coincidencia exacta
#                     if cell_str == target_lower:
#                         found_headers[target] = col_idx
                    
#                     # Coincidencia con variantes
#                     elif target in header_variants:
#                         for variant in header_variants[target]:
#                             if variant.lower() in cell_str:
#                                 found_headers[target] = col_idx
#                                 break
            
#             # Si encontramos varios headers en la misma fila, esta es la fila de headers
#             if len(found_headers) >= 3:
#                 header_row_idx = row_idx
#                 header_positions = found_headers
#                 print(f"✅ HEADERS REALES ENCONTRADOS en fila {row_idx}")
#                 print(f"   Headers y sus columnas: {found_headers}")
#                 break
        
#         if header_row_idx is None:
#             raise ValidationError("No se encontraron los headers requeridos en el Excel")
        
#         # ============================================
#         # 3. EXTRAER DATOS MANUALMENTE
#         # ============================================
#         print(f"\n📥 EXTRAYENDO DATOS DESDE FILA {header_row_idx + 1}...")
        
#         # Los datos empiezan en la fila DESPUÉS de los headers
#         data_start_row = header_row_idx + 1
        
#         # Preparar lista para almacenar datos
#         extracted_data = []
        
#         for row_idx in range(data_start_row, len(df_raw)):
#             row = df_raw.iloc[row_idx]
#             row_data = {}
#             has_valid_data = False
            
#             # Extraer cada campo según la posición de su header
#             for header_name, col_idx in header_positions.items():
#                 if col_idx < len(row):
#                     cell_value = row[col_idx]
                    
#                     # Limpiar el valor
#                     if pd.isna(cell_value):
#                         row_data[header_name] = ""
#                     else:
#                         value = str(cell_value).strip()
#                         row_data[header_name] = value
                        
#                         if value and value.lower() not in ['nan', 'none', '']:
#                             has_valid_data = True
#                 else:
#                     row_data[header_name] = ""
            
#             # Solo agregar filas con datos válidos
#             if has_valid_data:
#                 extracted_data.append(row_data)
        
#         if not extracted_data:
#             raise ValidationError("No se encontraron datos válidos después de los headers")
        
#         # ============================================
#         # 4. CREAR DATAFRAME CON DATOS EXTRAÍDOS
#         # ============================================
#         print(f"\n📊 CREANDO DATAFRAME CON {len(extracted_data)} FILAS...")
        
#         # Crear DataFrame
#         nuevo_df = pd.DataFrame(extracted_data)
        
#         # Asegurar que tengamos todas las columnas requeridas
#         required_columns = [
#             'alcance de evaluacion',
#             'funcionalidad',
#             'descripcion',
#             'criticidad',
#             'estado',
#             'otros'
#         ]
        
#         # Agregar columnas faltantes (vacías)
#         for col in required_columns:
#             if col not in nuevo_df.columns:
#                 nuevo_df[col] = ""
        
#         # Ordenar columnas
#         nuevo_df = nuevo_df[required_columns]
        
#         # ============================================
#         # 5. LIMPIEZA DE DATOS (CORREGIDO)
#         # ============================================
#         print("\n🧹 LIMPIANDO DATOS...")
        
#         original_count = len(nuevo_df)
        
#         # A. Eliminar filas donde 'descripcion' y 'criticidad' estén vacías
#         # ¡CORRECCIÓN IMPORTANTE: Usar paréntesis en operaciones lógicas con &
#         if len(nuevo_df) > 0:
#             # FORMA CORRECTA: Cada condición entre paréntesis
#             mask_valid = (
#                 (nuevo_df['descripcion'].astype(str).str.strip() != "") &
#                 (nuevo_df['criticidad'].astype(str).str.strip() != "")
#             )
#             nuevo_df = nuevo_df[mask_valid].copy()
        
#         # B. Asignar 'por_ejecutar' a estado
#         if 'estado' in nuevo_df.columns and len(nuevo_df) > 0:
#             nuevo_df['estado'] = 'por_ejecutar'
        
#         # C. Limpiar espacios en blanco
#         for col in nuevo_df.columns:
#             nuevo_df[col] = nuevo_df[col].apply(
#                 lambda x: str(x).strip() if pd.notna(x) and str(x).strip().lower() != 'nan' else ""
#             )
        
#         # D. Resetear índice
#         nuevo_df = nuevo_df.reset_index(drop=True)
        
#         # ============================================
#         # 6. VERIFICAR RESULTADO
#         # ============================================
#         if len(nuevo_df) == 0:
#             raise ValidationError("No hay datos válidos después del procesamiento")
        
#         print(f"\n✅ PROCESAMIENTO COMPLETADO:")
#         print(f"   - Headers encontrados en fila: {header_row_idx}")
#         print(f"   - Datos extraídos desde fila: {data_start_row}")
#         print(f"   - Filas originales extraídas: {original_count}")
#         print(f"   - Filas después de limpieza: {len(nuevo_df)}")
#         print(f"   - Filas eliminadas: {original_count - len(nuevo_df)}")
        
#         # Mostrar ejemplo REAL de datos
#         print(f"\n📋 EJEMPLO REAL DE DATOS PROCESADOS:")
#         if len(nuevo_df) > 0:
#             print(nuevo_df.head(3).to_string(index=False))
#             print("\n🔍 VALORES REALES (primeras filas):")
#             for i in range(min(3, len(nuevo_df))):
#                 print(f"Fila {i}:")
#                 for col in nuevo_df.columns:
#                     print(f"  {col}: '{nuevo_df.iloc[i][col]}'")
        
#         # ============================================
#         # 7. GUARDAR EN BUFFER
#         # ============================================
        
#         output = BytesIO()
        
#         with pd.ExcelWriter(output, engine='openpyxl') as writer:
#             nuevo_df.to_excel(writer, index=False, sheet_name='Matriz_Procesada')
        
#         output.seek(0)
        
#         return output, len(nuevo_df)
        
#     except ValidationError:
#         raise
#     except Exception as e:
#         print(f"❌ Error inesperado: {str(e)}")
#         import traceback
#         traceback.print_exc()
#         raise ValidationError(f"Error al procesar el archivo Excel: {str(e)}")