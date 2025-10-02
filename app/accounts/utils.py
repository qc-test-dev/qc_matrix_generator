from django import forms

def validar_formato_operativo(df):
    """Validador para matrices operativas (placeholder)"""
    # Por ahora solo verificamos que tenga datos
    if df.empty:
        raise forms.ValidationError("El archivo Excel está vacío")
    # Aquí irá la validación específica para operativos
    pass

def validar_formato_no_operativo(df):
    """Validador para matrices no operativas"""
    if df.empty:
        raise forms.ValidationError("El archivo Excel está vacío")
    
    # Obtener los encabezados (primera fila)
    headers = df.columns.tolist()
    
    # Convertir a minúsculas y limpiar espacios para comparación
    headers_clean = [str(header).strip().lower() for header in headers]
    
    # Encabezados esperados
    encabezados_esperados = [
        'alcance evaluación', 
        'fase', 
        'caso de prueba', 
        'estado', 
        'criticidad', 
        'nota sobre la prueba'
    ]
    
    for encabezado in encabezados_esperados:
        if encabezado not in headers_clean:
            raise forms.ValidationError(
                f"El archivo Excel no tiene el formato correcto. "
                f"Encabezado faltante: '{encabezado}'. "
                f"Encabezados encontrados: {headers}"
            )