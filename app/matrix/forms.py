from django import forms
from .models import SuperMatriz, Matriz, CasoDePrueba, Validate, TicketPorLevantar, DetallesValidate,Dispositivo
from django.contrib.auth import get_user_model
from ..accounts.models import Equipo
User = get_user_model()

class MatrizForm(forms.ModelForm):
    ALCANCE_CHOICES = [
        ('A', 'MVP (A)'),
        ('A,B', 'SMOKE TEST (A,B)'),
        ('A,B,C', 'NA (A,B,C)'),
    ]

    REGIONES = [
        ('Mexico', 'Mexico'),
        ('Dominicana','Dominicana'),
        ('Colombia', 'Colombia'),
        ('Ecuador', 'Ecuador'),
        ('Peru', 'Peru'), 
        ('Chile','Chile'),
        ('Argentina','Argentina'),
        ('Uruguay','Uruguay'),
        ('Paraguay','Paraguay'),
        ('Guatemala','Guatemala'),
        ('Salvador','Salvador'),
        ('Nicaragua','Nicaragua'),
        ('Costa Rica','Costa Rica'),
        ('Honduras','Honduras'),   
    ]

    alcance = forms.ChoiceField(
        choices=ALCANCE_CHOICES,
        widget=forms.RadioSelect,
        label='Alcance Evaluación',
        required=True
    )

    testers = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Testers"
    )

    regiones = forms.MultipleChoiceField(
        choices=REGIONES,
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Regiones"
    )

    dispositivo = forms.ModelChoiceField(
        queryset=Dispositivo.objects.none(),
        required=True,
        label="Dispositivo",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    nombre = forms.CharField(
    max_length=70,
    widget=forms.TextInput(attrs={
        'class': 'form-control',
        'maxlength': '75'
    })
)

    class Meta:
        model = Matriz
        fields = ['nombre', 'alcance', 'testers', 'regiones', 'dispositivo']

    def __init__(self, *args, **kwargs):
        equipo_nuevo = kwargs.pop('equipo_nuevo', None)
        super().__init__(*args, **kwargs)
        if equipo_nuevo:
            self.fields['testers'].queryset = User.objects.filter(equipo_nuevo=equipo_nuevo)
            self.fields['dispositivo'].queryset = Dispositivo.objects.filter(equipo=equipo_nuevo)


class CasoDePruebaForm(forms.ModelForm):
    ESTADO_CHOICES = [
        ('funciona', 'Funciona'),
        ('falla_nueva', 'Falla nueva'),
        ('falla_persistente', 'Falla persistente'),
        ('na', 'N/A'),
        ('pendiente', 'Pendiente'),
        ('por_ejecutar', 'Por ejecutar'),
    ]

    estado = forms.ChoiceField(
        choices=ESTADO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select estado-select'})
    )

    nota = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'style': 'resize: none;',"maxlength":"80"}),
        required=False
    )

    class Meta:
        model = CasoDePrueba
        fields = ['estado', 'nota']


class SuperMatrizForm(forms.ModelForm):
    nombre = forms.CharField(
        max_length=75,
        widget=forms.TextInput(attrs={'class': 'form-control', 'maxlength': '75'})
    )

    descripcion = forms.CharField(
        max_length=100,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'maxlength': '100'})
    )

    equipo_nuevo = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Equipo'
    )

    class Meta:
        model = SuperMatriz
        fields = ['nombre', 'descripcion', 'equipo_nuevo']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['equipo_nuevo'].queryset = Equipo.objects.all()


class ValidateForm(forms.ModelForm):
    class Meta:
        model = Validate
        fields = '__all__'
        exclude = ['super_matriz']


class TicketPorLevantarForm(forms.ModelForm):
    PRIORIDAD_CHOICES = [
        ('Bloqueante', 'Bloqueante'),
        ('Crítico', 'Crítico'),
    ]
    REGIONES = [
        ('Mexico', 'Mexico'),
        ('Dominicana','Dominicana'),
        ('Colombia', 'Colombia'),
        ('Ecuador', 'Ecuador'),
        ('Peru', 'Peru'), 
        ('Chile','Chile'),
        ('Argentina','Argentina'),
        ('Uruguay','Uruguay'),
        ('Paraguay','Paraguay'),
        ('Guatemala','Guatemala'),
        ('Salvador','Salvador'),
        ('Nicaragua','Nicaragua'),
        ('Costa Rica','Costa Rica'),
        ('Honduras','Honduras'),   
    ]

    tester = forms.ModelChoiceField(
        queryset=User.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Tester"
    )
    Region = forms.ChoiceField(choices=REGIONES, widget=forms.Select(attrs={'class': 'form-select'}))
    prioridad = forms.ChoiceField(choices=PRIORIDAD_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta:
        model = TicketPorLevantar
        fields = ['tester', 'ticket_SCT', 'BRF', 'Region', 'prioridad', 'desc', 'nota', 'url']
        widgets = {
            'ticket_SCT': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ticket SCT'}),
            'BRF': forms.TextInput(attrs={'class': 'form-control'}),
            'desc': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'nota': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'url': forms.URLInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super_matriz = kwargs.pop('super_matriz', None)
        super().__init__(*args, **kwargs)
        if super_matriz:
            equipo_nuevo = super_matriz.equipo_nuevo
            self.fields['tester'].queryset = User.objects.filter(equipo_nuevo=equipo_nuevo)


class ValidateEstadoForm(forms.ModelForm):
    class Meta:
        model = Validate
        fields = ['estado']
        widgets = {
            'estado': forms.Select(
                choices=[
                    ('funciona', 'Funciona'),
                    ('falla_nueva', 'Falla Nueva'),
                    ('falla_persistente', 'Falla Persistente'),
                    ('na', 'N/A'),
                    ('pendiente', 'Pendiente'),
                    ('por_ejecutar', 'Por Ejecutar')
                ],
                attrs={'class': 'form-select validate-estado'}
            ),
        }


class DetallesValidateForm(forms.ModelForm):
    testers = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Testers"
    )

    class Meta:
        model = DetallesValidate
        fields = ['filtro_RN', 'comentario_RN']
        widgets = {
            'filtro_RN': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Escribe el filtro aplicado por RN...',
                "maxlength80":"80",
            }),
            'comentario_RN': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'style': 'resize: none;',
                'placeholder': 'Agrega aquí los labels de RN'
            }),
        }
    def __init__(self, *args, **kwargs):
        equipo_nuevo = kwargs.pop('equipo_nuevo', None)
        super().__init__(*args, **kwargs)
        self.fields['filtro_RN'].required = False
        if equipo_nuevo:
            self.fields['testers'].queryset = User.objects.filter(equipo_nuevo=equipo_nuevo)
