from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.utils.translation import activate

from .forms import UserCreateForm, CustomPasswordChangeForm, AdminPasswordChangeForm
from .models import Equipo
from django.views.generic import ListView,DetailView
User = get_user_model()


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    success_url = '/'


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('accounts_app:login')


def is_admin(user):
    return user.is_authenticated and user.is_staff


@user_passes_test(is_admin)
def crear_usuario(request):
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            if User.objects.filter(username=username).exists():
                messages.warning(request, f"El usuario '{username}' ya existe.")
            else:
                user = form.save(commit=False)
                user.set_password(form.cleaned_data['password'])
                user.save()
                messages.success(request, f"Usuario '{username}' creado exitosamente.")
        else:
            messages.error(request, "Error en el formulario. Por favor verifica los campos.")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    return redirect('home')


@login_required
def cambiar_contraseña(request):
    activate('es')
    if request.method == 'POST':
        form = CustomPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Contraseña actualizada correctamente.')
            return redirect('home')
        else:
            messages.error(request, 'Por favor corrige los errores.')
    else:
        form = CustomPasswordChangeForm(user=request.user)
    return render(request, 'accounts/cambiar_contrasena.html', {'form': form})


@login_required
@user_passes_test(is_admin)
def cambiar_contrasena_usuario(request, user_id):
    usuario = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = AdminPasswordChangeForm(usuario, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f'Contraseña de {usuario.username} actualizada correctamente.')
            return redirect('accounts_app:lista_usuarios') 
        else:
            messages.error(request, 'Corrige los errores a continuación.')
    else:
        form = AdminPasswordChangeForm(usuario)
    return render(request, 'accounts/cambiar_contraseña_usuario.html', {'form': form, 'usuario': usuario})


@login_required
@user_passes_test(is_admin)
def lista_usuarios(request):
    equipo_seleccionado = request.GET.get('equipo')
    equipos = Equipo.objects.all()

    if equipo_seleccionado:
        usuarios = User.objects.filter(equipo_nuevo__id=equipo_seleccionado)
    else:
        usuarios = User.objects.all()

    return render(request, 'accounts/lista_usuarios.html', {
        'usuarios': usuarios,
        'equipos': equipos,
        'equipo_seleccionado': equipo_seleccionado
    })


class ListTeamsView(ListView):
    def get(self, request):
        teams = Equipo.objects.all().order_by('nombre')
        return render(request, 'teams/list_teams.html', {
            'equipos': teams
        })
class DispositivosEquipoView(DetailView):
    model = Equipo
    template_name = 'teams/dispositivos_equipo.html'
    context_object_name = 'equipo'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        equipo = self.get_object()
        
        # Obtener todos los dispositivos del equipo
        dispositivos = equipo.dispositivos.all()
        
        # Separar por estado operativo
        context['dispositivos_operativos'] = dispositivos.filter(operativo=True)
        context['dispositivos_no_operativos'] = dispositivos.filter(operativo=False)
        context['total_dispositivos'] = dispositivos.count()
        
        return context