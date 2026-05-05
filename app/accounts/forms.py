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
        archivo = self.cleaned_data.get('archivo_excel', None)  # Usar None por defecto
        
        if not archivo:
            raise ValidationError("Debe seleccionar un archivo Excel")
        
        # Validar extensión
        if not archivo.name.lower().endswith('.xlsx'):
            raise ValidationError("El archivo debe ser un Excel (.xlsx)")
        
        # Validar tamaño del archivo (50MB máximo)
        if archivo.size > 50 * 1024 * 1024:
            raise ValidationError("El archivo es demasiado grande. Tamaño máximo: 50MB")
        
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
                
                # Leer el Excel para buscar headers
                df_raw = pd.read_excel(archivo_excel, engine='openpyxl', header=None)
                
                if len(df_raw) == 0:
                    raise ValidationError("El archivo Excel está vacío")
                
                # HEADERS OBLIGATORIOS (6)
                required_headers = [
                    'alcance de evaluacion',
                    'funcionalidad',
                    'descripcion',
                    'criticidad',
                    'estado',
                    'otros'
                ]
                
                # VARIANTES DE HEADERS (español e inglés)
                variantes_headers = {
                    'alcance de evaluacion': ['alcance de evaluacion', 'alcance', 'alcance de evaluación', 'evaluacion', 'priority'],
                    'funcionalidad': ['funcionalidad', 'fase', 'section'],
                    'descripcion': ['descripcion', 'descripción', 'caso de prueba', 'caso prueba', 'test case name', 'description'],
                    'criticidad': ['criticidad', 'prioridad', 'severity level', 'severidad', 'severity'],
                    'estado': ['estado', 'status', 'situación', 'state'],
                    'otros': ['otros', 'comentarios', 'comentarios y datos de prueba', 'observaciones', 'nota', 'notas', 'others', 'notes'],
                    'id-prueba': ['id-prueba', 'id', 'id caso', 'id prueba', 'identificador', 'test case id'],
                    'tipo de usuario': ['tipo de usuario', 'tipo usuario', 'perfil usuario', 'rol', 'usuario', 'type', 'user type'],
                    'pasos a seguir': ['pasos a seguir', 'pasos', 'procedimiento', 'step by step', 'test step', 'step'],
                    'criterio aceptacion': ['criterio aceptacion', 'criterio de aceptacion', 'criterio aceptación', 'aceptacion', 'expected result']
                }
                
                # Buscar la fila de headers
                headers_encontrados = False
                fila_headers = None
                
                for idx_fila in range(min(50, len(df_raw))):
                    fila = df_raw.iloc[idx_fila]
                    temp_headers = []
                    
                    for celda in fila:
                        if pd.isna(celda):
                            continue
                        
                        celda_str = str(celda).strip()
                        celda_str_lower = celda_str.lower()
                        
                        # Buscar coincidencia con headers obligatorios
                        for header in required_headers:
                            # Coincidencia exacta
                            if celda_str_lower == header.lower():
                                if header not in temp_headers:
                                    temp_headers.append(header)
                                break
                            # Coincidencia con variantes
                            elif header in variantes_headers:
                                for variante in variantes_headers[header]:
                                    if celda_str_lower == variante.lower():
                                        if header not in temp_headers:
                                            temp_headers.append(header)
                                        break
                    
                    # Verificar si encontramos los 6 headers obligatorios
                    if len(temp_headers) == 6:
                        headers_encontrados = True
                        fila_headers = idx_fila + 1
                        break
                
                if not headers_encontrados:
                    raise ValidationError(
                        f"No se encontraron los 6 encabezados obligatorios.\n\n"
                        f"Encabezados requeridos (español/inglés):\n"
                        f"  • alcance de evaluacion / Priority\n"
                        f"  • funcionalidad / Section\n"
                        f"  • descripcion / Test Case Name\n"
                        f"  • criticidad / Severity Level\n"
                        f"  • estado / Status\n"
                        f"  • otros / Nota\n\n"
                        f"Los encabezados opcionales son:\n"
                        f"  • id-prueba / Test Case ID\n"
                        f"  • tipo de usuario / Type\n"
                        f"  • pasos a seguir / Test Step\n"
                        f"  • criterio aceptacion / Expected Result"
                    )
                
                # Restaurar posición del archivo
                archivo_excel.seek(0)
                
            except pd.errors.EmptyDataError:
                raise ValidationError("El archivo Excel está vacío o no se puede leer")
            except ValidationError:
                raise
            except Exception as e:
                if 'Workbook' in str(e) or 'openpyxl' in str(e):
                    raise ValidationError("El archivo no es un Excel válido o está corrupto")
                else:
                    raise ValidationError(f"Error al validar el archivo Excel: {str(e)}")
        
        return cleaned_data
    
    def save(self, commit=True):
        archivo_excel = self.cleaned_data.get('archivo_excel')
        equipo = self.cleaned_data.get('equipo')
        
        if not archivo_excel or not equipo:
            raise ValidationError("Faltan datos para procesar el archivo")
        
        try:
            archivo_excel.seek(0)
            excel_procesado, num_filas = procesar_excel_matriz(archivo_excel)
            
            nombre_original = archivo_excel.name
            nombre_base = os.path.basename(nombre_original)
            
            if '.' in nombre_base:
                nombre, extension = nombre_base.rsplit('.', 1)
                extension = '.' + extension
            else:
                nombre = nombre_base
                extension = ''
            
            nombres_existentes = list(Dispositivo.objects.filter(
                equipo=equipo
            ).values_list('matriz_base', flat=True))
            
            if nombre_base not in nombres_existentes:
                nombre_unico = nombre_base
            else:
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
            
            nombre_equipo_carpeta = equipo.nombre.replace(' ', '_').replace(',', '').replace('(', '').replace(')', '')
            ruta_final = f"{nombre_equipo_carpeta}/{nombre_unico}"
            
            dispositivo = super().save(commit=False)
            
            content_file = ContentFile(excel_procesado.getvalue())
            content_file.name = nombre_unico
            
            dispositivo.archivo_excel.save(ruta_final, content_file, save=False)
            dispositivo.matriz_base = nombre_unico
            
            excel_procesado.close()
            
            if commit:
                dispositivo.save()
            
            self.num_filas_procesadas = num_filas
            
            return dispositivo
            
        except Exception as e:
            raise ValidationError(f"Error al procesar y guardar el archivo Excel: {str(e)}")