import pandas as pd
import os
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.utils.translation import activate

from .forms import UserCreateForm, CustomPasswordChangeForm, AdminPasswordChangeForm
from .models import Equipo
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from app.matrix.forms import Dispositivo
from .forms import DispositivoForm
from django.conf import settings

from django.core.exceptions import PermissionDenied
from .utils import validar_formato_operativo, validar_formato_no_operativo,validar_archivo_duplicado
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
        context['dispositivos_operativos'] = equipo.dispositivos.filter(operativo=True)
        context['dispositivos_no_operativos'] = equipo.dispositivos.filter(operativo=False)
        context['total_dispositivos'] = equipo.dispositivos.count()
        
        return context
    
    def form_valid(self, form):
        try:
            # Guardar el dispositivo sin commit
            dispositivo = form.save(commit=False)
            
            # Obtener el nombre del archivo del formulario
            nombre_archivo = form.cleaned_data.get('nombre_archivo')
            archivo_excel = form.cleaned_data.get('archivo_excel')
            
            # Asignar el nombre del archivo al campo matriz_base
            dispositivo.matriz_base = nombre_archivo
            
            # Guardar el dispositivo
            dispositivo.save()
            
            # Guardar el archivo en static/excel_files/
            if archivo_excel:
                self.guardar_archivo_excel(archivo_excel, nombre_archivo)
            
            messages.success(self.request, f'Dispositivo "{dispositivo.nombre}" creado exitosamente.')
            return redirect('accounts_app:dispositivos_equipo', pk=dispositivo.equipo.id)
            
        except Exception as e:
            messages.error(self.request, f'Error al crear dispositivo: {str(e)}')
            return self.form_invalid(form)
    
    def guardar_archivo_excel(self, archivo, nombre_archivo):
        """Guarda el archivo Excel en la carpeta static/excel_files/"""
        excel_dir = os.path.join(settings.BASE_DIR, 'static', 'excel_files')
        os.makedirs(excel_dir, exist_ok=True)
        
        destino_path = os.path.join(excel_dir, nombre_archivo)
        
        # Guardar el archivo
        with open(destino_path, 'wb+') as destino:
            for chunk in archivo.chunks():
                destino.write(chunk)
        
class EditarDispositivoView(LoginAndLiderRequiredMixin, UpdateView):
    model = Dispositivo
    form_class = DispositivoForm
    template_name = 'teams/dispositivos_equipo.html'

    def get_object(self, queryset=None):
        dispositivo_id = self.kwargs.get('pk')
        equipo_id = self.kwargs.get('equipo_id')
        return get_object_or_404(Dispositivo, id=dispositivo_id, equipo_id=equipo_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        equipo_id = self.kwargs.get('equipo_id')
        equipo = get_object_or_404(Equipo, id=equipo_id)

        context['equipo'] = equipo
        context['dispositivos_operativos'] = equipo.dispositivos.filter(operativo=True)
        context['dispositivos_no_operativos'] = equipo.dispositivos.filter(operativo=False)
        context['total_dispositivos'] = equipo.dispositivos.count()
        context['abrir_modal_edicion'] = True  # Esto abrirá el modal automáticamente

        return context

    def get_success_url(self):
        equipo_id = self.kwargs.get('equipo_id')
        return reverse_lazy('accounts_app:dispositivos_equipo', kwargs={'pk': equipo_id})

    def form_valid(self, form):
        try:
            dispositivo = form.save(commit=False)
            
            # Manejar el archivo Excel si se subió uno nuevo
            archivo_excel = form.cleaned_data.get('archivo_excel')
            
            if archivo_excel:
                # Validar y procesar el archivo
                nombre_archivo = archivo_excel.name
                
                # Guardar el nombre en matriz_base
                dispositivo.matriz_base = nombre_archivo
                
                # Guardar el archivo físicamente
                self.guardar_archivo_excel(archivo_excel, nombre_archivo)
                
                # Si había un archivo anterior, eliminarlo si no es usado por otros
                dispositivo_original = self.get_object()
                if (dispositivo_original.matriz_base and 
                    dispositivo_original.matriz_base != nombre_archivo):
                    self.eliminar_archivo_anterior(dispositivo_original.matriz_base)
            else:
                # Si no se subió archivo nuevo, mantener el nombre actual
                dispositivo.matriz_base = self.get_object().matriz_base
            
            # Guardar el dispositivo
            dispositivo.save()
            
            messages.success(self.request, f'Dispositivo "{dispositivo.nombre}" actualizado correctamente.')
            return redirect(self.get_success_url())

        except Exception as e:
            messages.error(self.request, f"Error al actualizar el dispositivo: {str(e)}")
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Por favor corrige los errores en el formulario.")
        return super().form_invalid(form)

    def guardar_archivo_excel(self, archivo, nombre_archivo):
        """Guarda el archivo Excel en el sistema de archivos"""
        try:
            # Crear directorio si no existe
            excel_dir = os.path.join(settings.BASE_DIR, 'static', 'excel_files')
            os.makedirs(excel_dir, exist_ok=True)
            
            # Sanitizar nombre del archivo
            nombre_archivo = nombre_archivo.replace(' ', '_')
            
            # Ruta completa del archivo
            destino_path = os.path.join(excel_dir, nombre_archivo)
            
            # Guardar el archivo
            with open(destino_path, 'wb+') as destino:
                for chunk in archivo.chunks():
                    destino.write(chunk)
                    
            print(f"Archivo guardado: {destino_path}")
            
        except Exception as e:
            print(f"Error al guardar archivo: {str(e)}")
            raise

    def eliminar_archivo_anterior(self, nombre_archivo):
        """Elimina el archivo anterior si no es usado por otros dispositivos"""
        try:
            # Verificar si otros dispositivos usan este archivo
            otros_dispositivos = Dispositivo.objects.filter(matriz_base=nombre_archivo)
            
            if otros_dispositivos.count() == 0:
                excel_dir = os.path.join(settings.BASE_DIR, 'static', 'excel_files')
                archivo_path = os.path.join(excel_dir, nombre_archivo)
                
                if os.path.exists(archivo_path):
                    os.remove(archivo_path)
                    print(f"Archivo eliminado: {archivo_path}")
                    
        except Exception as e:
            print(f"Error al eliminar archivo: {str(e)}")
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
    if nombre_archivo:
        # Asumiendo que tu proyecto tiene una estructura estándar
        # con static/excel_files/ en la raíz del proyecto
        base_dir = settings.BASE_DIR
        file_path = os.path.join(base_dir, 'static', 'excel_files', str(nombre_archivo))
        
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                archivo_msg = f'Archivo "{nombre_archivo}" eliminado.'
            else:
                archivo_msg = f'Archivo "{nombre_archivo}" no encontrado.'
        except Exception as e:
            archivo_msg = f'Error al eliminar archivo: {str(e)}'
    else:
        archivo_msg = "No había archivo asociado."
    
    # Eliminar registro de la base de datos
    dispositivo.delete()
    
    messages.success(
        request,
        f'Dispositivo "{nombre_dispositivo}" eliminado. {archivo_msg}'
    )
    
    return redirect('accounts_app:dispositivos_equipo', pk=equipo_id)