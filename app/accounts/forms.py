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
        help_text='Seleccione el archivo .xlsx de la matriz base'
    )
    
    class Meta:
        model = Dispositivo
        fields = ['nombre', 'equipo', 'operativo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del dispositivo'}),
            'equipo': forms.Select(attrs={'class': 'form-control'}),
            'operativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_archivo_excel(self):
        archivo = self.cleaned_data.get('archivo_excel')
        if not archivo:
            raise forms.ValidationError("Debe seleccionar un archivo Excel")
        
        if not archivo.name.endswith('.xlsx'):
            raise forms.ValidationError("El archivo debe ser un Excel (.xlsx)")
        
        return archivo
    
    def clean(self):
        cleaned_data = super().clean()
        archivo_excel = cleaned_data.get('archivo_excel')
        operativo = cleaned_data.get('operativo')
        
        if archivo_excel:
            try:
                # Leer el archivo Excel
                df = pd.read_excel(archivo_excel)
                
                if operativo:
                    # Validar formato para operativos (placeholder)
                    validar_formato_operativo(df)
                else:
                    # Validar formato para no operativos
                    validar_formato_no_operativo(df)
                    
                # Guardar el nombre del archivo para después
                cleaned_data['nombre_archivo'] = archivo_excel.name
                
            except Exception as e:
                raise forms.ValidationError(f"Error al procesar el archivo Excel: {str(e)}")
        
        return cleaned_data