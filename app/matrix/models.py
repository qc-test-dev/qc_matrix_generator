# models.py
from django.db import models
from ..accounts.models import Equipo
from django.core.exceptions import ValidationError
from django.conf import settings
from django.core.files.storage import FileSystemStorage
import os
from django.utils import timezone
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
        # Guardar primero para obtener ID si es nuevo
        is_new = not self.pk
        
        # Si hay archivo Excel, procesarlo
        if self.archivo_excel and hasattr(self.archivo_excel, 'name'):
            # Generar nombre único para el archivo
            nombre_original = self.archivo_excel.name
            nombre_unico = self.generar_nombre_unico(nombre_original)
            
            # Crear nombre seguro para la carpeta del equipo
            nombre_equipo_carpeta = self.equipo.nombre.replace(' ', '_')
            
            # Establecer la ruta completa
            ruta_final = f"{nombre_equipo_carpeta}/{nombre_unico}"
            
            # Solo actualizar si la ruta es diferente
            if self.archivo_excel.name != ruta_final:
                # Crear directorio del equipo si no existe
                equipo_dir = os.path.join(settings.MEDIA_ROOT, 'excel', nombre_equipo_carpeta)
                os.makedirs(equipo_dir, exist_ok=True)
                
                # Actualizar campos
                self.archivo_excel.name = ruta_final
                self.matriz_base = nombre_unico
        
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