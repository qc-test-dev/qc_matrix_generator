from django import forms
from .models import User

CARGO_CHOICES=(('Lider','LIDER'),('Tester','TESTER'))
class UserCreateForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    nombre = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    apellido = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    cargo = forms.ChoiceField(choices=CARGO_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    class Meta:
        model = User
        fields = ['username', 'nombre', 'apellido', 'password', 'cargo']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }   