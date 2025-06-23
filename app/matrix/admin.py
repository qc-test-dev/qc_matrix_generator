from django.contrib import admin
from .models import SuperMatriz, CasoDePrueba, Matriz, Validate, DetallesValidate, TicketPorLevantar

# Inlines
class MatrizInline(admin.TabularInline):
    model = Matriz
    extra = 1

class CasoDePruebaInline(admin.TabularInline):
    model = CasoDePrueba
    extra = 1

# SuperMatriz Admin
class SuperMatrizAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'descripcion', 'equipo')  # quitamos 'fecha_creacion'
    search_fields = ('nombre', 'descripcion', 'equipo__nombre')
    list_filter = ('equipo',)
    ordering = ('id',)
    inlines = [MatrizInline]

# Matriz Admin
class MatrizAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'super_matriz')  # quitamos 'fecha_creacion'
    search_fields = ('nombre', 'super_matriz__nombre')
    list_filter = ('super_matriz',)
    ordering = ('id',)
    inlines = [CasoDePruebaInline]

# Validate Admin
class ValidateAdmin(admin.ModelAdmin):
    list_display = ('id', 'tester', 'ticket', 'super_matriz', 'estado',"prioridad")
    search_fields = ('tester', 'ticket', 'descripcion')
    list_filter = ('estado', 'super_matriz')
    ordering = ('id',)
    list_editable = ('estado',)

# TicketPorLevantar Admin
class TicketPorLevantarAdmin(admin.ModelAdmin):
    list_display = ('id', 'tester', 'ticket_SCT', 'super_matriz', 'prioridad')
    search_fields = ('tester__nombre', 'ticket_SCT', 'desc')
    list_filter = ('prioridad', 'super_matriz')
    ordering = ('id',)

# Registro de modelos
admin.site.register(SuperMatriz, SuperMatrizAdmin)
admin.site.register(Matriz, MatrizAdmin)
admin.site.register(CasoDePrueba)
admin.site.register(Validate, ValidateAdmin)
admin.site.register(DetallesValidate)
admin.site.register(TicketPorLevantar, TicketPorLevantarAdmin)
