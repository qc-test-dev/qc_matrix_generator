from django.urls import path
from .views import CustomLoginView, CustomLogoutView, crear_usuario
app_name = 'accounts_app'
urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('crear_usuario/', crear_usuario, name='crear_usuario'),
]
