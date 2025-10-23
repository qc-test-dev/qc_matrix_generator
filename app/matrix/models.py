# models.py
from django.db import models
from ..accounts.models import Equipo
from django.core.exceptions import ValidationError
from django.conf import settings
class Dispositivo(models.Model):
    nombre = models.CharField(max_length=75)
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='dispositivos')
    matriz_base = models.CharField(max_length=75)  # Nombre del archivo .xlsx
    operativo = models.BooleanField(
        default=False,
        blank=True,
        null=True,
        verbose_name="Operativo"
    )

    def __str__(self):
        return f"{self.nombre}"
    
    def get_excel_url(self):
        """Retorna la URL estática del archivo Excel"""
        if self.matriz_base:
            filename = self.matriz_base
            if not filename.lower().endswith('.xlsx'):
                filename += '.xlsx'
            return f"{settings.STATIC_URL}excel_files/{filename}"
        return None
    
    def get_excel_path(self):
        """Retorna la ruta física del archivo Excel"""
        if self.matriz_base:
            filename = self.matriz_base
            if not filename.lower().endswith('.xlsx'):
                filename += '.xlsx'
            
            # Buscar específicamente en static/excel_files/
            static_path = os.path.join(settings.BASE_DIR, 'static', 'excel_files', filename)
            if os.path.exists(static_path):
                return static_path
            
            # Fallback: usar staticfiles finder
            found_path = find(f'excel_files/{filename}')
            return found_path
        
        return None
    
    def excel_exists(self):
        """Verifica si el archivo Excel existe en static/excel_files/"""
        path = self.get_excel_path()
        exists = path is not None and os.path.exists(path)
        print(f"Buscando archivo: {self.matriz_base}")
        print(f"Ruta: {path}")
        print(f"¿Existe?: {exists}")
        return exists
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