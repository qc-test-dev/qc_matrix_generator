from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from .forms import UserCreateForm
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import update_session_auth_hash
from django.utils.translation import activate
from .forms import CustomPasswordChangeForm,AdminPasswordChangeForm
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
    equipos = User.EQUIPO_CHOICES

    if equipo_seleccionado:
        usuarios = User.objects.filter(equipo=equipo_seleccionado)
    else:
        usuarios = User.objects.all()

    return render(request, 'accounts/lista_usuarios.html', {
        'usuarios': usuarios,
        'equipos': equipos,
        'equipo_seleccionado': equipo_seleccionado
    })