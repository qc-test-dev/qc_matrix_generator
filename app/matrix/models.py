# models.py
from django.db import models
from ..accounts.models import Equipo
from django.core.exceptions import ValidationError
from django.conf import settings
from django.core.files.storage import FileSystemStorage
import os
from django.utils import timezone
import pandas as pd , re 
# Configurar storage para archivos Excel
excel_storage = FileSystemStorage(
    location=os.path.join(settings.MEDIA_ROOT, 'excel'),
    base_url=os.path.join(settings.MEDIA_URL, 'excel')
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
        
        Ejemplo:
        - Si 'reporte.xlsx' ya existe → 'reporte_1.xlsx'
        - Si 'reporte.xlsx' y 'reporte_1.xlsx' existen → 'reporte_2.xlsx'
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
    # Si hay archivo Excel, procesarlo ANTES de guardar
        if self.archivo_excel and hasattr(self.archivo_excel, 'file'):
            try:
                # Procesar el Excel
                excel_procesado, num_filas = procesar_excel_matriz(self.archivo_excel.file)
                
                # Generar nombre único para el archivo
                nombre_original = self.archivo_excel.name
                nombre_unico = self.generar_nombre_unico(nombre_original)
                
                # Crear nombre seguro para la carpeta del equipo
                nombre_equipo_carpeta = self.equipo.nombre.replace(' ', '_')
                ruta_final = f"{nombre_equipo_carpeta}/{nombre_unico}"
                
                # Ruta completa del archivo
                ruta_completa = os.path.join(settings.MEDIA_ROOT, 'excel', nombre_equipo_carpeta, nombre_unico)
                os.makedirs(os.path.dirname(ruta_completa), exist_ok=True)
                
                # Guardar el archivo procesado
                with open(ruta_completa, 'wb') as f:
                    f.write(excel_procesado.read())
                
                # Actualizar campos
                self.archivo_excel.name = ruta_final
                self.matriz_base = nombre_unico
                
                # Podrías querer guardar el número de filas en algún campo
                # self.num_casos_prueba = num_filas
                
            except Exception as e:
                # Si hay error en el procesamiento, no guardar
                raise ValidationError(f"Error al procesar el archivo Excel: {str(e)}")
    
    # Guardar el objeto

        
        # Guardar el objeto
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
def procesar_excel_matriz(archivo_excel):
    """
    Procesa el archivo Excel según los requisitos:
    - Busca y mapea headers flexibles a los 6 headers requeridos
    - Limpia datos innecesarios
    - Establece estado = 'por_ejecutar' para todas las filas
    - Guarda nuevo Excel procesado
    
    Retorna el archivo procesado (BytesIO)
    """
    try:
        # Leer el archivo Excel
        df = pd.read_excel(archivo_excel, engine='openpyxl')
        
        # Limpiar nombres de columnas: minúsculas, sin espacios extra
        df.columns = [str(col).strip().lower() for col in df.columns]
        print(f"📄 Columnas encontradas en Excel: {df.columns.tolist()}")
        
        # Mapeo FLEXIBLE de columnas del Excel a los 6 headers requeridos
        # Formato: {'header_final': ['posibles_nombres_en_excel', ...]}
        mapeo_flexible = {
            'alcance de evaluacion': [
                'alcance de evaluacion', 'alcance de evaluación', 
                'alcance'
            ],
            'funcionalidad': [
                'funcionalidad', 'fase', 
            ],
            'descripcion': [
                'descripcion', 'descripción', 'caso de prueba', 
                'caso prueba', 'prueba'
            ],
            'criticidad': [
                'criticidad', 'prioridad', 'importancia', 
                'severidad', 'gravedad', 'nivel'
            ],
            'estado': [
                'estado', 'status', 'situacion', 'condición'
            ],
            'otros': [
                'otros', 'comentarios', 'comentarios y datos de prueba',
                'notas', 'datos',
                
            ]
        }
        
        # Headers requeridos FINALES (en este orden)
        headers_requeridos = [
            'alcance de evaluacion',
            'funcionalidad',
            'descripcion',
            'criticidad',
            'estado',
            'otros'
        ]
        
        # Diccionario para mapear: header_requerido → header_encontrado
        columnas_encontradas = {}
        
        print("\n🔍 Buscando coincidencias...")
        
        # Para cada header requerido, buscar coincidencias en las columnas del Excel
        for header_final, posibles_nombres in mapeo_flexible.items():
            mejor_coincidencia = None
            mejor_puntaje = 0
            
            for col_excel in df.columns:
                col_excel_clean = col_excel.strip().lower()
                
                # Calcular puntaje de coincidencia
                puntaje = 0
                
                for posible in posibles_nombres:
                    posible_clean = posible.strip().lower()
                    
                    # 1. Coincidencia EXACTA (puntaje alto)
                    if col_excel_clean == posible_clean:
                        puntaje = 100
                        break
                    
                    # 2. El nombre del Excel CONTIENE la palabra clave
                    elif posible_clean in col_excel_clean:
                        # Dar más puntaje si la coincidencia es larga
                        puntaje = max(puntaje, len(posible_clean) * 10)
                    
                    # 3. La palabra clave CONTIENE el nombre del Excel
                    elif col_excel_clean in posible_clean:
                        puntaje = max(puntaje, len(col_excel_clean) * 8)
                    
                    # 4. Coincidencia de palabras individuales
                    palabras_col = set(col_excel_clean.split())
                    palabras_posible = set(posible_clean.split())
                    if palabras_col & palabras_posible:  # Intersección
                        puntaje = max(puntaje, 5)
                
                # Actualizar mejor coincidencia
                if puntaje > mejor_puntaje:
                    mejor_puntaje = puntaje
                    mejor_coincidencia = col_excel
            
            # Si encontramos una coincidencia razonable, la asignamos
            if mejor_coincidencia and mejor_puntaje >= 5:
                columnas_encontradas[header_final] = mejor_coincidencia
                print(f"  ✅ '{mejor_coincidencia}' → '{header_final}' (puntaje: {mejor_puntaje})")
            else:
                print(f"  ❌ No se encontró coincidencia para '{header_final}'")
        
        print(f"\n📋 Resumen de mapeo:")
        for req, encontrado in columnas_encontradas.items():
            print(f"  {req} ← {encontrado}")
        
        # Verificar columnas ESENCIALES mínimas
        columnas_esenciales = ['descripcion', 'criticidad']
        for col_esencial in columnas_esenciales:
            if col_esencial not in columnas_encontradas:
                # Intentar buscar manualmente
                for col_excel in df.columns:
                    col_lower = col_excel.lower()
                    if col_esencial == 'descripcion' and any(p in col_lower for p in ['caso', 'descrip', 'prueba']):
                        columnas_encontradas[col_esencial] = col_excel
                        print(f"  🔍 Encontrada '{col_excel}' como '{col_esencial}' (búsqueda manual)")
                        break
                    elif col_esencial == 'criticidad' and any(p in col_lower for p in ['critic', 'prior']):
                        columnas_encontradas[col_esencial] = col_excel
                        print(f"  🔍 Encontrada '{col_excel}' como '{col_esencial}' (búsqueda manual)")
                        break
                
                # Si aún no se encontró, error
                if col_esencial not in columnas_encontradas:
                    raise ValidationError(
                        f"No se encontró la columna '{col_esencial}' o equivalente. "
                        f"Columnas en el archivo: {df.columns.tolist()}"
                    )
        
        # Crear nuevo DataFrame con las columnas requeridas
        nuevo_df = pd.DataFrame()
        
        for header_final in headers_requeridos:
            if header_final in columnas_encontradas:
                header_original = columnas_encontradas[header_final]
                nuevo_df[header_final] = df[header_original]
                print(f"  📥 Copiando datos: '{header_original}' → '{header_final}'")
            else:
                # Si no se encontró, crear columna vacía
                nuevo_df[header_final] = ""
                print(f"  📝 Columna '{header_final}' creada vacía")
        
        # Ordenar columnas en el orden correcto
        nuevo_df = nuevo_df[headers_requeridos]
        
        # LIMPIEZA DE DATOS
        print("\n🧹 Limpiando datos...")
        
        # 1. Eliminar filas completamente vacías
        filas_iniciales = len(nuevo_df)
        nuevo_df = nuevo_df.dropna(how='all')
        filas_despues_vacias = len(nuevo_df)
        print(f"  - Filas eliminadas (vacías): {filas_iniciales - filas_despues_vacias}")
        
        # 2. Eliminar filas donde 'descripcion' esté vacío
        if 'descripcion' in nuevo_df.columns and len(nuevo_df) > 0:
            mask_descripcion_valida = (
                nuevo_df['descripcion'].notna() & 
                (nuevo_df['descripcion'].astype(str).str.strip() != "")
            )
            nuevo_df = nuevo_df[mask_descripcion_valida]
            print(f"  - Filas con 'descripcion' válida: {len(nuevo_df)}")
        
        # 3. Asignar valor por defecto a 'estado'
        if 'estado' in nuevo_df.columns and len(nuevo_df) > 0:
            nuevo_df['estado'] = 'por_ejecutar'
            print(f"  - Estado asignado: 'por_ejecutar' para todas las filas")
        
        # Resetear índice
        nuevo_df = nuevo_df.reset_index(drop=True)
        
        # Verificar que haya datos
        if len(nuevo_df) == 0:
            raise ValidationError("No hay datos válidos después del procesamiento.")
        
        print(f"\n✅ Resultado final:")
        print(f"  - Filas procesadas: {len(nuevo_df)}")
        print(f"  - Columnas: {list(nuevo_df.columns)}")
        
        # Mostrar primeras filas para debug
        if len(nuevo_df) > 0:
            print(f"\n📋 Vista previa de datos:")
            print(nuevo_df.head(3).to_string())
        
        # Guardar en buffer
        from io import BytesIO
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            nuevo_df.to_excel(writer, index=False, sheet_name='Matriz_Procesada')
        
        output.seek(0)
        
        return output, len(nuevo_df)
        
    except ValidationError:
        raise
    except Exception as e:
        raise ValidationError(f"Error al procesar Excel: {str(e)}")