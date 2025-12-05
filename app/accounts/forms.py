from django import forms
from .models import User, Equipo
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.core.exceptions import ValidationError
from .utils import validar_formato_no_operativo,validar_formato_operativo
from app.matrix.models import Dispositivo
import pandas as pd
import re

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
        required=True  # Asegurar que siempre sea requerido
    )
    
    class Meta:
        model = Dispositivo
        fields = ['nombre', 'equipo', 'operativo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del dispositivo'}),
            'equipo': forms.Select(attrs={'class': 'form-control'}),
            'operativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacer que archivo_excel no sea requerido en edición
        if self.instance and self.instance.pk:
            self.fields['archivo_excel'].required = False
    
    def clean_archivo_excel(self):
        archivo = self.cleaned_data.get('archivo_excel')
        
        # Si no hay archivo y estamos editando, es válido (no se cambia)
        if not archivo and self.instance and self.instance.pk:
            return None
        
        # Si no hay archivo y estamos creando, error
        if not archivo:
            raise forms.ValidationError("Debe seleccionar un archivo Excel")
        
        # Validar extensión
        if not archivo.name.endswith('.xlsx'):
            raise forms.ValidationError("El archivo debe ser un Excel (.xlsx)")
        
        return archivo
    
    def clean(self):
        cleaned_data = super().clean()
        archivo_excel = cleaned_data.get('archivo_excel')
        operativo = cleaned_data.get('operativo')
        
        # Solo validar si hay un archivo nuevo
        if archivo_excel:
            try:
                # Validar duplicados
                self.validar_archivo_duplicado(archivo_excel)
                
                # Leer y validar el archivo Excel
                archivo_excel.seek(0)  # Asegurar que podemos leer el archivo
                df = pd.read_excel(archivo_excel)
                
                if operativo:
                    validar_formato_operativo(df)
                else:
                    validar_formato_no_operativo(df)
                
                # Guardar el nombre del archivo
                cleaned_data['nombre_archivo'] = archivo_excel.name
                
                # Restaurar posición del archivo para guardarlo después
                archivo_excel.seek(0)
                
            except forms.ValidationError:
                raise  # Re-lanzar errores de validación específicos
            except Exception as e:
                raise forms.ValidationError(f"Error al procesar el archivo Excel: {str(e)}")
        
        return cleaned_data
    
    def validar_archivo_duplicado(self, archivo_excel):
        """Valida que el nombre del archivo no esté duplicado."""
        nombre_archivo = archivo_excel.name
        
        # Buscar si hay otro dispositivo con el mismo nombre de archivo
        qs = Dispositivo.objects.filter(matriz_base=nombre_archivo)
        
        # Si estamos editando, excluir el dispositivo actual
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        
        if qs.exists():
            # Obtener información sobre el dispositivo duplicado
            dispositivo_duplicado = qs.first()
            raise forms.ValidationError(
                f'El archivo "{nombre_archivo}" ya está siendo usado por el dispositivo '
                f'"{dispositivo_duplicado.nombre}" (Equipo: {dispositivo_duplicado.equipo.nombre}). '
                f'Por favor, use un archivo con un nombre diferente o renombre el archivo actual.'
            )