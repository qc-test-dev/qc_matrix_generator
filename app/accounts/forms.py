from django import forms
from .models import User
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.forms import SetPasswordForm
from django.core.exceptions import ValidationError
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

CARGO_CHOICES=(('Lider','LIDER'),('Tester','TESTER'))
EQUIPO_CHOICES=(
    ('Claro TV STB - IPTV - Roku - TATA','Claro TV STB - IPTV - Roku - TATA'),
    ('STV (LG,Samsung,ADR), Kepler-FireTV, STV2(Hisense,Netrange)','STV (LG,Samsung,ADR), Kepler-FireTV, STV2(Hisense,Netrange)'),
    ('IPTV AOSP','IPTV AOSP'),
    ('WIN - WEB - Fire TV','WIN - WEB - Fire TV'),
    ('IOS - TvOS','IOS - TvOS'),
    ('Android','Android'),
    ('Smart TV AAF','Smart TV AAF')
    )
class UserCreateForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    nombre = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    apellido = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    cargo = forms.ChoiceField(choices=CARGO_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    equipo = forms.ChoiceField(choices=EQUIPO_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    class Meta:
        model = User
        fields = ['username', 'nombre', 'apellido', 'password', 'cargo','equipo']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }
class AdminPasswordChangeForm(SetPasswordForm):
    class Meta:
        model = User
        fields = ['new_password1', 'new_password2']   