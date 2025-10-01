from django.urls import path
from django.contrib.auth import views as auth_views
from .views import CustomLoginView, CustomLogoutView, crear_usuario,cambiar_contrasena_usuario,lista_usuarios,cambiar_contraseña, ListTeamsView,DispositivosEquipoView

app_name = 'accounts_app'
urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('crear_usuario/', crear_usuario, name='crear_usuario'),
    path('cambiar-contrasena/', cambiar_contraseña, name='cambiar_contraseña'),
    path('admin/usuarios/', lista_usuarios, name='lista_usuarios'),
    path('admin/cambiar-contrasena/<int:user_id>/',cambiar_contrasena_usuario, name='cambiar_contrasena_usuario'),
    path('equipos/', ListTeamsView.as_view(), name='list_teams'),
    path('equipo/<int:pk>/dispositivos/', DispositivosEquipoView.as_view(), name='dispositivos_equipo'),
]
