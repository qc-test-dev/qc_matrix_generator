from django.contrib import admin
# from .models import CustomUser
from .models import User,Equipo
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'nombre', 'apellido', 'cargo', 'equipo','equipo_nuevo')
    search_fields = ('username', 'nombre', 'apellido')
    list_filter = ('cargo', 'equipo')

@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)