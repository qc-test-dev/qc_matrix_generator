from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import get_valid_filename
from django.conf import settings
import pandas as pd
from io import BytesIO
def procesar_excel_matriz(archivo_excel):
    """
    Procesa el archivo Excel y retorna BytesIO con el archivo procesado.
    """
    try:
        # ============================================
        # 1. LEER EXCEL CRUDO
        # ============================================
        df_raw = pd.read_excel(archivo_excel, engine='openpyxl', header=None)
        
        # ============================================
        # 2. DEFINIR ENCABEZADOS
        # ============================================
        # HEADERS OBLIGATORIOS (6)
        required_headers = [
            'alcance de evaluacion',
            'funcionalidad', 
            'descripcion',
            'criticidad',
            'estado',
            'otros'
        ]
        
        optional_headers = [
            'id-prueba',
            'tipo de usuario',
            'pasos a seguir',
            'criterio aceptacion'
        ]
        
        all_target_headers = required_headers + optional_headers
        
        # Variantes de cada header (incluyendo todas las posibles variantes de STEP BY STEP)
        header_variants = {
            'alcance de evaluacion': ['alcance de evaluacion', 'alcance', 'evaluacion', 'priority'],
            'funcionalidad': ['funcionalidad', 'fase', 'section'],
            'descripcion': ['descripcion', 'descripción', 'caso de prueba', 'desc', 'test case name', 'description'],
            'criticidad': ['criticidad', 'prioridad', 'severidad', 'severity level', 'severity'],
            'estado': ['estado', 'status', 'situación', 'state'],
            'otros': ['otros', 'comentarios', 'observaciones', 'notas', 'nota', 'others', 'notes'],
            'id-prueba': ['id-prueba', 'id', 'id caso', 'id prueba', 'identificador', 'test case id'],
            'tipo de usuario': ['tipo de usuario', 'tipo usuario', 'perfil usuario', 'rol', 'usuario', 'type', 'user type'],
            # VARIANTES COMPLETAS PARA STEP BY STEP
            'pasos a seguir': [
                'pasos a seguir', 
                'pasos', 
                'procedimiento', 
                'step by step', 
                'test step', 
                'step',
                '"step by step"',           # Con comillas dobles
                "'step by step'",           # Con comillas simples
                'STEP BY STEP',             # Mayúsculas
                '"STEP BY STEP"',           # Con comillas y mayúsculas
                'step-by-step',             # Con guiones
                'step_by_step',             # Con guiones bajos
                'teststep',                 # Sin espacio
                'test-step',                # Con guión
                'paso a paso'               # En español
            ],
            'criterio aceptacion': ['criterio aceptacion', 'criterio de aceptacion', 'criterio aceptación', 'aceptacion', 'expected result']
        }
        
        # ============================================
        # 3. LIMPIAR Y BUSCAR LA FILA CON LOS HEADERS
        # ============================================
        header_row_idx = None
        column_mapping = {}
        
        for row_idx in range(min(100, len(df_raw))):
            row = df_raw.iloc[row_idx]
            temp_mapping = {}
            
            for col_idx, cell in enumerate(row):
                if pd.isna(cell):
                    continue
                
                # Limpiar el header: eliminar comillas, espacios extras, convertir a minúsculas
                cell_str = str(cell).strip()
                # Eliminar comillas dobles y simples
                cell_str_clean = cell_str.replace('"', '').replace("'", '')
                # Eliminar espacios múltiples
                import re
                cell_str_clean = re.sub(r'\s+', ' ', cell_str_clean)
                cell_str_lower = cell_str_clean.strip().lower()
                
                # También conservar la versión original para comparaciones exactas
                cell_str_original = cell_str.strip()
                
                if len(cell_str_lower) < 2:
                    continue
                
                for target in all_target_headers:
                    variants = header_variants.get(target, [target])
                    
                    # Coincidencia exacta con target limpio
                    if cell_str_lower == target:
                        temp_mapping[target] = col_idx
                        break
                    
                    # Coincidencia con variantes (comparando versión limpia)
                    for variant in variants:
                        variant_clean = variant.replace('"', '').replace("'", '').strip().lower()
                        if cell_str_lower == variant_clean:
                            temp_mapping[target] = col_idx
                            break
                        
                        # También comparar con la versión original por si acaso
                        if cell_str_original == variant:
                            temp_mapping[target] = col_idx
                            break
            
            # Verificar si encontramos los 6 headers obligatorios
            found_required = [h for h in required_headers if h in temp_mapping]
            
            if len(found_required) == 6:
                header_row_idx = row_idx
                column_mapping = temp_mapping
                print(f"✅ Headers encontrados: {list(column_mapping.keys())}")
                break
        
        if header_row_idx is None:
            raise ValidationError(
                f"No se encontraron los encabezados obligatorios: {', '.join(required_headers)}\n\n"
                f"Encabezados requeridos (español/inglés):\n"
                f"  • alcance de evaluacion / Priority\n"
                f"  • funcionalidad / Section\n"
                f"  • descripcion / Test Case Name\n"
                f"  • criticidad / Severity Level\n"
                f"  • estado / Status\n"
                f"  • otros / Nota"
            )
        
        # ============================================
        # 4. EXTRAER DATOS
        # ============================================
        data_rows = []
        
        for row_idx in range(header_row_idx + 1, len(df_raw)):
            row = df_raw.iloc[row_idx]
            
            if row.isna().all():
                continue
            
            row_data = {}
            has_data = False
            
            for std_header, col_idx in column_mapping.items():
                if col_idx < len(row):
                    value = row[col_idx]
                    
                    if pd.isna(value):
                        row_data[std_header] = ""
                    else:
                        value_str = str(value).strip()
                        if value_str.lower() in ['nan', 'none', 'null', '']:
                            row_data[std_header] = ""
                        else:
                            row_data[std_header] = value_str
                            if std_header in required_headers and value_str:
                                has_data = True
                else:
                    row_data[std_header] = ""
            
            for header in optional_headers:
                if header not in row_data:
                    row_data[header] = ""
            
            if has_data:
                data_rows.append(row_data)
        
        if not data_rows:
            raise ValidationError("No se encontraron datos válidos después de los encabezados")
        
        # ============================================
        # 5. CREAR DATAFRAME
        # ============================================
        nuevo_df = pd.DataFrame(data_rows)
        
        for col in all_target_headers:
            if col not in nuevo_df.columns:
                nuevo_df[col] = ""
        
        # ============================================
        # 6. LIMPIAR ID-PRUEBA
        # ============================================
        valores_no_id = ['blocker', 'bloqueante', 'critical', 'critico', 'alta', 'media', 'baja']
        
        if 'id-prueba' in nuevo_df.columns:
            nuevo_df['id-prueba'] = nuevo_df['id-prueba'].apply(
                lambda x: "" if str(x).strip().lower() in valores_no_id or not str(x).strip() else str(x).strip()
            )
        
        # ============================================
        # 7. NORMALIZAR CRITICIDAD
        # ============================================
        def normalizar_criticidad(valor):
            if not valor or valor == '':
                return ''
            v = str(valor).strip().lower()
            if 'blocker' in v or 'bloqueante' in v:
                return 'Bloqueante'
            if 'critical' in v or 'critico' in v:
                return 'Crítico'
            if 'alta' in v:
                return 'Alta'
            if 'media' in v:
                return 'Media'
            if 'baja' in v:
                return 'Baja'
            return str(valor).strip()
        
        if 'criticidad' in nuevo_df.columns:
            nuevo_df['criticidad'] = nuevo_df['criticidad'].apply(normalizar_criticidad)
        
        # ============================================
        # 8. REORDENAR Y RENOMBRAR
        # ============================================
        column_order = [
            'id-prueba', 'alcance de evaluacion', 'funcionalidad', 'tipo de usuario',
            'descripcion', 'pasos a seguir', 'criterio aceptacion', 'criticidad', 'estado', 'otros'
        ]
        
        for col in column_order:
            if col not in nuevo_df.columns:
                nuevo_df[col] = ""
        
        nuevo_df = nuevo_df[column_order]
        
        # Renombrar para la salida final
        nuevo_df = nuevo_df.rename(columns={
            'pasos a seguir': 'STEP BY STEP',
            'id-prueba': 'ID-prueba',
            'alcance de evaluacion': 'Alcance de evaluacion',
            'funcionalidad': 'Funcionalidad',
            'tipo de usuario': 'Tipo de usuario',
            'descripcion': 'Descripcion',
            'criterio aceptacion': 'Criterio aceptación',
            'criticidad': 'Criticidad',
            'estado': 'Estado',
            'otros': 'Otros'
        })
        
        # ============================================
        # 9. LIMPIEZA FINAL
        # ============================================
        for col in nuevo_df.columns:
            nuevo_df[col] = nuevo_df[col].astype(str).str.strip()
            nuevo_df[col] = nuevo_df[col].replace(['nan', 'None', 'NaN', 'none', 'null'], '')
        
        if 'Estado' in nuevo_df.columns:
            nuevo_df['Estado'] = nuevo_df['Estado'].apply(lambda x: 'por ejecutar' if x == '' else x)
        
        # Eliminar columnas extras (headers de más se ignoran)
        columnas_finales = ['ID-prueba', 'Alcance de evaluacion', 'Funcionalidad', 'Tipo de usuario', 
                           'Descripcion', 'STEP BY STEP', 'Criterio aceptación', 'Criticidad', 'Estado', 'Otros']
        
        for col in nuevo_df.columns:
            if col not in columnas_finales:
                nuevo_df = nuevo_df.drop(columns=[col])
        
        nuevo_df = nuevo_df.reset_index(drop=True)
        
        # ============================================
        # 10. GUARDAR RESULTADO
        # ============================================
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            nuevo_df.to_excel(writer, index=False, sheet_name='Matriz_Procesada')
        
        output.seek(0)
        
        return output, len(nuevo_df)
        
    except ValidationError:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise ValidationError(f"Error al procesar el archivo Excel: {str(e)}")
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