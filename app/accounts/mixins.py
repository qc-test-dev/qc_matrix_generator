from django.contrib.auth.mixins import LoginRequiredMixin, AccessMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.conf import settings
from django.shortcuts import get_object_or_404
from .models import Equipo
class LiderRequiredMixin(AccessMixin):
    """Mixin que verifica si el usuario es Lider"""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if request.user.cargo != "Lider":
            raise PermissionDenied(
                "Acceso denegado. Se requieren permisos de Lider para acceder a esta página."
            )
        
        return super().dispatch(request, *args, **kwargs)

class LoginAndLiderRequiredMixin(LoginRequiredMixin, LiderRequiredMixin):
    """Mixin combinado que requiere login y ser Lider"""
    pass

class LiderPermissionMixin:
    """Mixin alternativo más sencillo"""
    
    def check_permissions(self, request):
        """Método para verificar permisos"""
        if not request.user.is_authenticated:
            return False
        
        if request.user.cargo != "Lider":
            return False
        
        return True
    
    def dispatch(self, request, *args, **kwargs):
        if not self.check_permissions(request):
            if not request.user.is_authenticated:
                return redirect(settings.LOGIN_URL)
            raise PermissionDenied("No tienes permisos de Lider")
        
        return super().dispatch(request, *args, **kwargs)

class EquipoLiderMixin(LiderRequiredMixin):
    """Mixin que además verifica que el Lider tenga acceso al equipo específico"""
    
    def get_equipo(self):
        """Obtiene el equipo del contexto"""
        equipo_id = self.kwargs.get('equipo_id') or self.kwargs.get('pk')
        return get_object_or_404(Equipo, id=equipo_id)
    
    def dispatch(self, request, *args, **kwargs):
        # Primero verifica que sea Lider
        response = super().dispatch(request, *args, **kwargs)
        
        # Lógica adicional: verificar acceso al equipo específico
        
        return response