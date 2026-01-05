from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import get_valid_filename
from ..matrix.models import Dispositivo 
from django.conf import settings
import os


# def validar_formato_operativo(df):
#     """Validador para matrices operativas"""
#     if df.empty:
#         raise forms.ValidationError("El archivo Excel está vacío")
    
#     # Obtener los encabezados (primera fila)
#     headers = df.columns.tolist()
    
#     # Convertir a minúsculas y quitar espacios extras
#     headers_clean = [str(header).strip().lower() for header in headers]
    
#     # los encabezados que mencionaste (en minúsculas, sin acentos)
#     encabezados_esperados = [
#         'id caso',
#         'alcance de evaluacion',
#         'funcionalidad',
#         'tipo de usuario',
#         'descripcion',
#         'pasos a seguir',
#         'criticidad',
#         'estado',
#         'otros'
#     ]
    
#     # Verificar CADA encabezado esperado
#     for encabezado in encabezados_esperados:
#         if encabezado not in headers_clean:
#             raise forms.ValidationError(
#                 f"El archivo Excel operativo no tiene el formato correcto. "
#                 f"Encabezado faltante: '{encabezado}'. "
#                 f"Encabezados encontrados: {headers}"
#             )
    
#     # Validar que haya al menos una fila de datos
#     if len(df) == 0:
#         raise forms.ValidationError("El archivo Excel no contiene datos (solo encabezados)")
    
#     return True

# def validar_formato_no_operativo(df):
#     """Validador para matrices no operativas"""
#     if df.empty:
#         raise forms.ValidationError("El archivo Excel está vacío")
    
#     # Obtener los encabezados (primera fila)
#     headers = df.columns.tolist()
    
#     # Convertir a minúsculas y quitar espacios extras
#     headers_clean = [str(header).strip().lower() for header in headers]
    
#     # Encabezados esperados SIN ACENTOS (en minúsculas)
#     encabezados_esperados = [
#         'alcance de evaluacion',  
#         'funcionalidad', 
#         'descripcion',             
#         'estado', 
#         'criticidad', 
#         'otros'
#     ]
    
#     # Verificar cada encabezado esperado
#     for encabezado in encabezados_esperados:
#         if encabezado not in headers_clean:
#             raise forms.ValidationError(
#                 f"El archivo Excel no tiene el formato correcto. "
#                 f"Encabezado faltante: '{encabezado}'. "
#                 f"Encabezados encontrados: {headers}"
#             )
    
#     return True
# def validar_archivo_duplicado(nombre_archivo, dispositivo_actual=None):
#     """
#     Valida que el nombre del archivo no esté duplicado.
    
#     Args:
#         nombre_archivo: Nombre del archivo a verificar
#         dispositivo_actual: Instancia actual del dispositivo (para edición)
    
#     Returns:
#         Tupla (nombre_final, es_duplicado)
#     """
#     excel_dir = os.path.join(settings.BASE_DIR, 'static', 'excel_files')
    
#     # Limpiar el nombre del archivo
#     nombre_limpio = get_valid_filename(nombre_archivo)
    
#     # Verificar si ya existe un dispositivo con ese nombre de archivo
#     # Buscar si hay otro dispositivo con el mismo nombre de archivo
#     dispositivos_con_mismo_archivo = Dispositivo.objects.filter(
#         matriz_base=nombre_limpio
#     )
    
#     # Si estamos editando, excluir el dispositivo actual
#     if dispositivo_actual and dispositivo_actual.id:
#         dispositivos_con_mismo_archivo = dispositivos_con_mismo_archivo.exclude(
#             id=dispositivo_actual.id
#         )
    
#     if dispositivos_con_mismo_archivo.exists():
#         return nombre_limpio, True
#     return nombre_limpio, False