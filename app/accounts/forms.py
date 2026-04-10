from django import forms
from .models import User, Equipo
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.core.exceptions import ValidationError
# from .utils import validar_formato_no_operativo,validar_formato_operativo
from app.matrix.models import Dispositivo
from app.matrix.models import procesar_excel_matriz
from django.core.files.base import ContentFile
import pandas as pd
import re,os

class CustomPasswordChangeForm(PasswordChangeForm):
    def clean_new_password1(self):
        password = self.cleaned_data.get('new_password1')

        if len(password) < 8:
            raise ValidationError("La contraseña debe tener al menos 8 caracteres.")
        if not password[0].isupper():
            raise ValidationError("La primera letra debe ser mayúscula.")
        if not re.search(r'\d', password):
            raise ValidationError("La contraseña debe contener al menos un número.")

        return password

CARGO_CHOICES = (('Lider', 'LIDER'), ('Tester', 'TESTER'))

class UserCreateForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    nombre = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    apellido = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    cargo = forms.ChoiceField(choices=CARGO_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    equipo_nuevo = forms.ModelChoiceField(
        queryset=Equipo.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,  # o True si lo quieres obligatorio
        label='Equipo'
    )

    class Meta:
        model = User
        fields = ['username', 'nombre', 'apellido', 'password', 'cargo', 'equipo_nuevo']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }

class AdminPasswordChangeForm(SetPasswordForm):
    class Meta:
        model = User
        fields = ['new_password1', 'new_password2']
class DispositivoForm(forms.ModelForm):
    archivo_excel = forms.FileField(
        label='Archivo Excel',
        help_text='Seleccione el archivo .xlsx de la matriz base',
        required=True,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.xlsx'
        })
    )
    
    class Meta:
        model = Dispositivo
        fields = ['nombre', 'equipo', 'archivo_excel']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Nombre de la matriz'
            }),
            'equipo': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def clean_archivo_excel(self):
        archivo = self.cleaned_data.get('archivo_excel')
        
        if not archivo:
            raise ValidationError("Debe seleccionar un archivo Excel")
        
        # Validar extensión
        if not archivo.name.lower().endswith('.xlsx'):
            raise ValidationError("El archivo debe ser un Excel (.xlsx)")
        
        # Validar tamaño del archivo (opcional, 50MB máximo)
        if archivo.size > 50 * 1024 * 1024:  # 50MB
            raise ValidationError("El archivo es demasiado grande. Tamaño máximo: 10MB")
        
        return archivo
    
    def clean(self):
        cleaned_data = super().clean()
        equipo = cleaned_data.get('equipo')
        archivo_excel = cleaned_data.get('archivo_excel')
        
        if not equipo:
            raise ValidationError("Debe seleccionar un equipo")
        
        if archivo_excel:
            try:
                # Validar que el Excel tenga los headers correctos
                archivo_excel.seek(0)
                
                # Leer el Excel COMPLETO para buscar headers
                df_raw = pd.read_excel(archivo_excel, engine='openpyxl', header=None)
                
                # Verificar que el Excel tenga datos
                if len(df_raw) == 0:
                    raise ValidationError("El archivo Excel está vacío")
                
                # NUEVOS HEADERS REQUERIDOS
                headers_buscados = [
                    'id-prueba',
                    'alcance de evaluacion',
                    'funcionalidad',
                    'tipo de usuario',
                    'descripcion', 
                    'pasos a seguir',
                    'criticidad',
                    'estado',
                    'otros',
                    'criterio aceptacion'
                ]
                
                # NUEVAS VARIANTES DE HEADERS
                variantes_headers = {
                    'id-prueba': ['id-prueba', 'id', 'id caso', 'id prueba', 'identificador'],
                    'alcance de evaluacion': ['alcance de evaluación', 'alcance'],
                    'funcionalidad': ['fase', 'funcionalidad'],
                    'tipo de usuario': ['tipo de usuario', 'tipo usuario', 'perfil usuario', 'rol'],
                    'descripcion': ['descripción', 'caso de prueba', 'caso prueba', 'descripcion'],
                    'pasos a seguir': ['STEP BY STEP', 'pasos', 'pasos a seguir','"STEP BY STEP"' ],
                    'criticidad': ['prioridad', 'criticidad'],
                    'estado': ['status', 'estado', 'situación'],
                    'otros': ['comentarios', 'comentarios y datos de prueba', 'observaciones'],
                    'criterio aceptacion': ['criterio aceptacion', 'criterio de aceptacion', 'criterio aceptación', 'condiciones aceptación']
                }
                
                # Buscar en cada fila (igual que en procesar_excel_matriz)
                headers_encontrados = False
                fila_headers = None
                
                for idx_fila in range(min(50, len(df_raw))):
                    fila = df_raw.iloc[idx_fila]
                    coincidencias = 0
                    headers_encontrados_fila = []
                    
                    for celda in fila:
                        if pd.isna(celda):
                            continue
                            
                        celda_str = str(celda).strip().lower()
                        
                        # Buscar cada header en esta celda
                        for header in headers_buscados:
                            header_lower = header.lower()
                            
                            if celda_str == header_lower:
                                coincidencias += 1
                                headers_encontrados_fila.append(header)
                                break
                            elif header in variantes_headers:
                                for variante in variantes_headers[header]:
                                    variante_lower = variante.lower()
                                    if variante_lower in celda_str or celda_str in variante_lower:
                                        coincidencias += 1
                                        headers_encontrados_fila.append(header)
                                        break
                    
                    # Necesitamos encontrar al menos 8 de los 10 headers (80% para ser flexible)
                    if coincidencias >= 8:
                        headers_encontrados = True
                        fila_headers = idx_fila + 1
                        #print(f"✅ Validación: {coincidencias} de {len(headers_buscados)} headers encontrados en fila {fila_headers}")
                        break
                
                if not headers_encontrados:
                    # Crear mensaje detallado de los headers requeridos
                    mensaje_headers = "\n".join([f"  • {h}" for h in headers_buscados])
                    raise ValidationError(
                        f"No se encontraron los headers requeridos en el Excel.\n\n"
                        f"El archivo debe contener al menos 8 de los siguientes 10 headers:\n"
                        f"{mensaje_headers}\n\n"
                        f"Headers encontrados: Revise que los nombres de las columnas sean correctos."
                    )
                
                # Restaurar posición del archivo
                archivo_excel.seek(0)
                
            except pd.errors.EmptyDataError:
                raise ValidationError("El archivo Excel está vacío o no se puede leer")
            except Exception as e:
                # Mensaje de error más amigable
                if 'Workbook' in str(e) or 'openpyxl' in str(e):
                    raise ValidationError("El archivo no es un Excel válido o está corrupto")
                else:
                    raise ValidationError(f"Error al validar el archivo Excel: {str(e)}")
        
        return cleaned_data
    
    def save(self, commit=True):
        # Primero, procesar el Excel
        archivo_excel = self.cleaned_data.get('archivo_excel')
        equipo = self.cleaned_data.get('equipo')
        
        if not archivo_excel or not equipo:
            raise ValidationError("Faltan datos para procesar el archivo")
        
        try:
            # 1. Procesar el Excel
            archivo_excel.seek(0)
            excel_procesado, num_filas = procesar_excel_matriz(archivo_excel)
            
            # 2. Generar nombre único
            nombre_original = archivo_excel.name
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
                equipo=equipo
            ).values_list('matriz_base', flat=True))
            
            # Si el nombre original no existe, usarlo
            if nombre_base not in nombres_existentes:
                nombre_unico = nombre_base
            else:
                # Si existe, buscar el siguiente número disponible
                contador = 1
                while True:
                    nombre_propuesto = f"{nombre}_{contador}{extension}"
                    
                    if nombre_propuesto not in nombres_existentes:
                        nombre_unico = nombre_propuesto
                        break
                    
                    contador += 1
                    
                    if contador > 100:
                        import time
                        timestamp = int(time.time())
                        nombre_unico = f"{nombre}_{timestamp}{extension}"
                        break
            
            # 3. Crear nombre seguro para la carpeta del equipo
            nombre_equipo_carpeta = equipo.nombre.replace(' ', '_').replace(',', '').replace('(', '').replace(')', '')
            
            # 4. Construir la ruta final
            ruta_final = f"{nombre_equipo_carpeta}/{nombre_unico}"
            
            # 5. Obtener la instancia del dispositivo
            dispositivo = super().save(commit=False)
            
            # 6. Guardar el archivo procesado usando el storage
            # Crear ContentFile desde el buffer
            content_file = ContentFile(excel_procesado.getvalue())
            
            # Asignar nombre al content file
            content_file.name = nombre_unico
            
            # Guardar usando el storage (esto manejará la ruta completa)
            dispositivo.archivo_excel.save(ruta_final, content_file, save=False)
            
            # 7. Actualizar campos
            dispositivo.matriz_base = nombre_unico
            
            # 8. Cerrar buffers
            excel_procesado.close()
            
            # 9. Guardar el dispositivo si commit=True
            if commit:
                dispositivo.save()
            
            # Guardar número de filas para usar en la vista
            self.num_filas_procesadas = num_filas
            
            return dispositivo
            
        except Exception as e:
            raise ValidationError(f"Error al procesar y guardar el archivo Excel: {str(e)}")