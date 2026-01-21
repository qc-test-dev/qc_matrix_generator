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
        # print(f"\n LEYENDO EXCEL CRUDO...")
        
        # # Leer el Excel COMPLETO sin headers
        df_raw = pd.read_excel(archivo_excel, engine='openpyxl', header=None)
        # print(f" Excel crudo: {df_raw.shape[0]} filas, {df_raw.shape[1]} columnas")
        
        # # ============================================
        # # 2. BUSCAR LA FILA CON LOS HEADERS REALES
        # # ============================================
        # print(f"\n BUSCANDO HEADERS REALES...")
        
        # Los headers que realmente buscamos
        target_headers = [
            'alcance de evaluacion',
            'funcionalidad',
            'descripcion',
            'criticidad',
            'estado',
            'otros'
        ]
        
        # También aceptar variantes
        header_variants = {
            'alcance de evaluacion': ['alcance de evaluación', 'alcance'],
            'funcionalidad': ['fase', 'funcionalidad o fase'],
            'descripcion': ['descripción', 'caso de prueba', 'caso prueba'],
            'criticidad': ['prioridad'],
            'estado': ['status'],
            'otros': ['comentarios', 'comentarios y datos de prueba']
        }
        
        header_row_idx = None
        header_positions = {}  # {header_name: column_index}
        
        for row_idx in range(min(50, len(df_raw))):
            row = df_raw.iloc[row_idx]
            found_headers = {}
            
            # Buscar cada header en esta fila
            for col_idx, cell in enumerate(row):
                if pd.isna(cell):
                    continue
                    
                cell_str = str(cell).strip().lower()
                
                # Buscar cada header target
                for target in target_headers:
                    target_lower = target.lower()
                    
                    # Coincidencia exacta
                    if cell_str == target_lower:
                        found_headers[target] = col_idx
                    
                    # Coincidencia con variantes
                    elif target in header_variants:
                        for variant in header_variants[target]:
                            if variant.lower() in cell_str:
                                found_headers[target] = col_idx
                                break
            
            # Si encontramos varios headers en la misma fila, esta es la fila de headers
            if len(found_headers) >= 3:
                header_row_idx = row_idx
                header_positions = found_headers
                # print(f" HEADERS REALES ENCONTRADOS en fila {row_idx}")
                # print(f"   Headers y sus columnas: {found_headers}")
                break
        
        if header_row_idx is None:
            raise ValidationError("No se encontraron los headers requeridos en el Excel")
        
        # ============================================
        # 3. EXTRAER DATOS MANUALMENTE
        # ============================================
        #print(f"\n📥 EXTRAYENDO DATOS DESDE FILA {header_row_idx + 1}...")
        
        # Los datos empiezan en la fila DESPUÉS de los headers
        data_start_row = header_row_idx + 1
        
        # Preparar lista para almacenar datos
        extracted_data = []
        
        for row_idx in range(data_start_row, len(df_raw)):
            row = df_raw.iloc[row_idx]
            row_data = {}
            has_valid_data = False
            
            # Extraer cada campo según la posición de su header
            for header_name, col_idx in header_positions.items():
                if col_idx < len(row):
                    cell_value = row[col_idx]
                    
                    # Limpiar el valor
                    if pd.isna(cell_value):
                        row_data[header_name] = ""
                    else:
                        value = str(cell_value).strip()
                        row_data[header_name] = value
                        
                        if value and value.lower() not in ['nan', 'none', '']:
                            has_valid_data = True
                else:
                    row_data[header_name] = ""
            
            # Solo agregar filas con datos válidos
            if has_valid_data:
                extracted_data.append(row_data)
        
        if not extracted_data:
            raise ValidationError("No se encontraron datos válidos después de los headers")
        
        # ============================================
        # 4. CREAR DATAFRAME CON DATOS EXTRAÍDOS
        # ============================================
        #print(f"\n CREANDO DATAFRAME CON {len(extracted_data)} FILAS...")
        
        # Crear DataFrame
        nuevo_df = pd.DataFrame(extracted_data)
        
        # Asegurar que tengamos todas las columnas requeridas
        required_columns = [
            'alcance de evaluacion',
            'funcionalidad',
            'descripcion',
            'criticidad',
            'estado',
            'otros'
        ]
        
        # Agregar columnas faltantes (vacías)
        for col in required_columns:
            if col not in nuevo_df.columns:
                nuevo_df[col] = ""
        
        # Ordenar columnas
        nuevo_df = nuevo_df[required_columns]
        
        # ============================================
        # 5. LIMPIEZA DE DATOS
        # ============================================
        #print("\n🧹 LIMPIANDO DATOS...")
        
        original_count = len(nuevo_df)
        
        # A. Eliminar filas donde 'descripcion' y 'criticidad' estén vacías
        if len(nuevo_df) > 0:
            mask_valid = (
                (nuevo_df['descripcion'].astype(str).str.strip() != "") &
                (nuevo_df['criticidad'].astype(str).str.strip() != "")
            )
            nuevo_df = nuevo_df[mask_valid].copy()
        
        # B. Asignar 'por_ejecutar' a estado
        if 'estado' in nuevo_df.columns and len(nuevo_df) > 0:
            nuevo_df['estado'] = 'por ejecutar'
        
        # C. Limpiar espacios en blanco
        for col in nuevo_df.columns:
            nuevo_df[col] = nuevo_df[col].apply(
                lambda x: str(x).strip() if pd.notna(x) and str(x).strip().lower() != 'nan' else ""
            )
        
        # D. Resetear índice
        nuevo_df = nuevo_df.reset_index(drop=True)
        
        # ============================================
        # 6. VERIFICAR RESULTADO
        # ============================================
        if len(nuevo_df) == 0:
            raise ValidationError("No hay datos válidos después del procesamiento")
        
        # print(f"\n PROCESAMIENTO COMPLETADO:")
        # print(f"   - Headers encontrados en fila: {header_row_idx}")
        # print(f"   - Datos extraídos desde fila: {data_start_row}")
        # print(f"   - Filas originales extraídas: {original_count}")
        # print(f"   - Filas después de limpieza: {len(nuevo_df)}")
        
        # ============================================
        # 7. GUARDAR EN BUFFER
        # ============================================
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            nuevo_df.to_excel(writer, index=False, sheet_name='Matriz_Procesada')
        
        output.seek(0)
        
        return output, len(nuevo_df)
        
    except ValidationError:
        raise
    except Exception as e:
        #print(f"❌ Error inesperado: {str(e)}")
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