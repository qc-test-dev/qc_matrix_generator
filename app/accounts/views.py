from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from .forms import UserCreateForm
from django.contrib import messages
from django.contrib.auth import get_user_model

User = get_user_model()  # SOLO ESTA LÍNEA PARA OBTENER TU MODELO PERSONALIZADO

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
    return redirect('home')
