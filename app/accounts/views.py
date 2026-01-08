import pandas as pd
import os
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.utils.translation import activate
from django.http import FileResponse
from .forms import UserCreateForm, CustomPasswordChangeForm, AdminPasswordChangeForm
from .models import Equipo
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from app.matrix.forms import Dispositivo
from .forms import DispositivoForm
from django.conf import settings

from django.core.exceptions import PermissionDenied
# from .utils import validar_formato_operativo, validar_formato_no_operativo,validar_archivo_duplicado
from .mixins import LoginAndLiderRequiredMixin

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
class ListTeamsView(LoginAndLiderRequiredMixin, ListView):
    def get(self, request):
        teams = Equipo.objects.all().order_by('nombre')
        return render(request, 'teams/list_teams.html', {
            'equipos': teams
        })

class DispositivosEquipoView(LoginAndLiderRequiredMixin, DetailView):
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

class CrearDispositivoView(LoginAndLiderRequiredMixin, CreateView):
    model = Dispositivo
    form_class = DispositivoForm
    template_name = 'teams/dispositivos_equipo.html'
    
    def get_success_url(self):
        return reverse_lazy('accounts_app:dispositivos_equipo', kwargs={'pk': self.object.equipo.id})
    
    def get_form_kwargs(self):
        """Pasar el equipo_id al formulario para preseleccionarlo"""
        kwargs = super().get_form_kwargs()
        equipo_id = self.kwargs.get('equipo_id')
        
        if 'initial' not in kwargs:
            kwargs['initial'] = {}
        
        if equipo_id:
            kwargs['initial']['equipo'] = equipo_id
            
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        equipo_id = self.kwargs.get('equipo_id')
        equipo = get_object_or_404(Equipo, id=equipo_id)
        
        # Agregar el contexto necesario para el template de lista
        context['equipo'] = equipo
        context['dispositivos'] = equipo.dispositivos.all()  # Cambiado a todos
        context['total_dispositivos'] = equipo.dispositivos.count()
        
        return context
    
    def form_valid(self, form):
        try:
            # Obtener el equipo
            equipo_id = self.kwargs.get('equipo_id')
            equipo = get_object_or_404(Equipo, id=equipo_id)
            
            # Guardar el dispositivo (ya procesa el Excel en save())
            dispositivo = form.save(commit=False)
            dispositivo.equipo = equipo
            
            # Obtener número de filas procesadas (si está disponible)
            num_filas = getattr(form, 'num_filas_procesadas', 0)
            
            dispositivo.save()
            
            mensaje = f'Matriz "{dispositivo.nombre}" creada exitosamente.'
            if num_filas:
                mensaje += f' Se procesaron {num_filas} casos de prueba.'
            
            messages.success(self.request, mensaje)
            return redirect('accounts_app:dispositivos_equipo', pk=equipo.id)
            
        except Exception as e:
            messages.error(self.request, f'Error al crear matriz: {str(e)}')
            return self.form_invalid(form)
@login_required
def descargar_excel(request, equipo_id, dispositivo_id):
    """Descarga el archivo Excel"""
    dispositivo = get_object_or_404(Dispositivo, id=dispositivo_id, equipo_id=equipo_id)
    
    if dispositivo.excel_exists():
        file_path = dispositivo.get_excel_path()
        file = open(file_path, 'rb')
        response = FileResponse(file, as_attachment=True, filename=dispositivo.get_filename())
        return response
    else:
        messages.error(request, "El archivo no existe")
        return redirect('accounts_app:dispositivos_equipo', pk=equipo_id)
@login_required
def eliminar_dispositivo(request, equipo_id, dispositivo_id):
    """Vista para eliminar un dispositivo y su archivo Excel asociado"""
    
    if request.user.cargo != "Lider":
        raise PermissionDenied("No tienes permisos para eliminar dispositivos")
    
    dispositivo = get_object_or_404(Dispositivo, id=dispositivo_id, equipo_id=equipo_id)
    
    if request.method != 'POST':
        return render(request, 'accounts_app/confirmar_eliminar.html', {
            'dispositivo': dispositivo,
            'equipo_id': equipo_id
        })
    
    nombre_dispositivo = dispositivo.nombre
    nombre_archivo = dispositivo.matriz_base
    
    # Eliminar archivo Excel si existe
    archivo_msg = ""
    if nombre_archivo and dispositivo.archivo_excel:
        try:
            # Usar el método delete del FileField (más seguro)
            dispositivo.archivo_excel.delete(save=False)
            archivo_msg = f'Archivo "{nombre_archivo}" eliminado correctamente.'
            
        except Exception as e:
            # Si falla, intentar eliminar manualmente
            try:
                # Construir la ruta correcta según tu configuración
                # Basado en tu código: 'excel/{nombre_equipo_carpeta}/{nombre_unico}'
                
                # Obtener la ruta del archivo desde el modelo
                file_path = dispositivo.get_excel_path()
                
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                    archivo_msg = f'Archivo "{nombre_archivo}" eliminado manualmente.'
                else:
                    archivo_msg = f'Archivo "{nombre_archivo}" no encontrado en disco.'
                    
            except Exception as e2:
                archivo_msg = f'Error al eliminar archivo: {str(e2)}'
    else:
        archivo_msg = "No había archivo asociado."
    
    # Eliminar registro de la base de datos
    dispositivo.delete()
    
    messages.success(
        request,
        f'Dispositivo "{nombre_dispositivo}" eliminado. {archivo_msg}'
    )
    
    return redirect('accounts_app:dispositivos_equipo', pk=equipo_id)