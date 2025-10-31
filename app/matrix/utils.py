import openpyxl
from .models import CasoDePrueba,Validate
from requests.auth import HTTPBasicAuth
from decouple import config
from collections import defaultdict
from resources.url_jira import JIRA_URL
import pandas as pd
import re
import requests
import random
import os,json
from .models import Matriz,SuperMatriz
from app.accounts.models import Equipo
from django.db.models import Q, F
import openpyxl
from .models import CasoDePrueba

JIRA_EMAIL,JIRA_API_TOKEN = os.getenv('JIRA_EMAIL'),os.getenv('JIRA_API_TOKEN')
print(JIRA_API_TOKEN,JIRA_EMAIL)
def limpiar(valor):
    if isinstance(valor, str):
        return valor.strip()
    return valor


import openpyxl
from .models import CasoDePrueba  # ajusta el import según tu estructura

def importar_matriz_desde_excel(matriz, ruta_excel, alcances_permitidos=None):
    """
    Importa casos de prueba desde un archivo Excel y los asigna a una matriz.
    Usa los nombres de encabezado reales del archivo.
    Filtra por alcance si se proporciona una lista de alcances_permitidos.
    """
    wb = openpyxl.load_workbook(ruta_excel)
    sheet = wb.active

    # Leer la primera fila como encabezados
    encabezados = [str(celda).strip().lower() for celda in next(sheet.iter_rows(min_row=1, max_row=1, values_only=True))]

    # Crear mapa de encabezados normalizados -> índice
    columnas = {nombre: i for i, nombre in enumerate(encabezados)}

    for fila in sheet.iter_rows(min_row=2, values_only=True):
        # Extraer los datos según el nombre de la columna
        etiqueta = fila[columnas.get("etiqueta")]
        alcance = fila[columnas.get("alcance de evaluación")]
        fase = fila[columnas.get("fase")]
        tipo_usuario = fila[columnas.get("tipo de usuario")]
        caso_de_prueba = fila[columnas.get("caso de prueba")]
        medio_pago = fila[columnas.get("medio de pago")]
        monto = fila[columnas.get("monto")]
        criticidad = fila[columnas.get("criticidad")]
        estado = "por_ejecutar"
        navegador = fila[columnas.get("navegador")]
        comentarios = fila[columnas.get("comentarios y datos de prueba")]
        pasos = fila[columnas.get("pasos")]

        # Validar campos clave
        if not (alcance and fase and caso_de_prueba and criticidad):
            continue

        # Filtrar por alcance
        if alcances_permitidos and alcance not in alcances_permitidos:
            continue

        # Crear el caso de prueba
        CasoDePrueba.objects.create(
            matriz=matriz,
            alcance=alcance,
            fase=fase,
            caso_de_prueba=caso_de_prueba,
            estado=estado or "por_ejecutar",
            criticidad=criticidad,
            nota=comentarios or "",
            etiqueta=etiqueta,
            tipo_usuario=tipo_usuario,
            pasos=pasos,
            mdp=medio_pago,
            monto=monto,
            navegador=navegador
        )



# def importar_validates_desde_excel(super_matriz, ruta_excel):
#     """
#     Importa registros de 'Validate' desde un archivo Excel y los asigna a una SuperMatriz.
#     Las filas incompletas (sin tester, ticket, descripcion, prioridad o estado) se ignoran.
#     """
#     wb = openpyxl.load_workbook(ruta_excel)
#     sheet = wb.active

#     empty_rows = 0

#     for fila in sheet.iter_rows(min_row=2, values_only=True):
#         if all(cell is None for cell in fila):
#             empty_rows += 1
#             if empty_rows > 5:
#                 break
#             #print("Fila ignorada por estar incompleta")
#             continue
#         empty_rows = 0  # Reset counter si hay datos

#         tester = fila[0]
#         ticket = fila[1]
#         descripcion = fila[2]
#         prioridad = fila[3]
#         estado = fila[4]

#         # Ignorar si falta alguno de los campos obligatorios
#         if not tester or not ticket or not descripcion or not prioridad or not estado:
#             #print("Fila ignorada por campos vacíos obligatorios")
#             continue

#         Validate.objects.create(
#             super_matriz=super_matriz,
#             tester=tester,
#             ticket=ticket,
#             descripcion=descripcion,
#             prioridad=prioridad,
#             estado=estado
#         )

def importar_validates(super_matriz, link, testers_qs):
    # Evitar errores si el link está vacío o es None
    if not link:
        print("El link está vacío o es None. No se puede importar validates.")
        return

    # Convertir queryset a lista de nombres completos
    TESTERS = [
        f"{t.nombre} {t.apellido}".strip()
        for t in testers_qs
    ]

    if not TESTERS:
        print("No hay testers disponibles para asignar.")
        return

    issues, error = fetch_jira_issues(link)
    if error:
        print(f"Error al obtener issues: {error}")
        return

    if not issues:
        print("No se encontraron issues.")
        return

    random.shuffle(issues)

    tester_count = len(TESTERS)
    assignments = {tester: [] for tester in TESTERS}

    for idx, caso in enumerate(issues):
        assigned_tester = TESTERS[idx % tester_count]
        assignments[assigned_tester].append(caso)

    validate_objects = []
    for tester, casos in assignments.items():
        for caso in casos:
            validate_objects.append(
                Validate(
                    super_matriz=super_matriz,
                    tester=tester,
                    ticket=caso["key"],
                    descripcion=caso["summary"],
                    prioridad=caso["priority"],
                    estado="por_ejecutar"
                )
            )
    Validate.objects.bulk_create(validate_objects)
def fetch_jira_issues(filter_link):
    match = re.search(r'filter=(\d+)', filter_link)
    if not match:
        return None, "No se pudo extraer el filtro del enlace."

    filter_id = match.group(1)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    try:
        # Obtener el JQL del filtro
        #https://dlatvarg.atlassian.net/issues/?filter=56761
        filter_url = f"{JIRA_URL['jira_url_filter']}{filter_id}"
        filter_resp = requests.get(
            filter_url,
            headers={"Accept": "application/json"},
            auth=HTTPBasicAuth(config('JIRA_EMAIL'), config('JIRA_API_TOKEN'))
        )
        filter_resp.raise_for_status()
        jql = filter_resp.json().get("jql")
        if not jql:
            return None, "El filtro no tiene JQL definido."

        # Endpoint correcto para la nueva API
        search_url = "https://dlatvarg.atlassian.net/rest/api/3/search/jql"
        payload = {"jql": jql, "maxResults": 50, "fields": ["summary","description","priority"]}
        resp = requests.post(
            search_url,
            headers=headers,
            auth=HTTPBasicAuth(config('JIRA_EMAIL'), config('JIRA_API_TOKEN')),
            data=json.dumps(payload)
        )
        resp.raise_for_status()
        data = resp.json()

        issues = []
        for issue in data.get("issues", []):
            fields = issue.get("fields", {})
            issues.append({
                "key": issue.get("key"),
                "summary": fields.get("summary"),
                "description": fields.get("description", "Sin descripción"),
                "priority": fields.get("priority", {}).get("name", "Sin prioridad")
            })

    except requests.RequestException as e:
        return None, f"Error al obtener issues: {e}"
    except json.JSONDecodeError:
        return None, "No se pudo decodificar la respuesta de Jira."

    if not issues:
        return None, "No se encontraron issues."

    return issues, None

def matriz_info(matrices):
    matrices_info = []
    for matriz in matrices:
        casos = matriz.casos.all()
        total_casos = casos.count()
        estados_interes = ['funciona', 'falla_nueva', 'falla_persistente', "na","pendiente_por_externo"]
        casos_filtrados = casos.filter(estado__in=estados_interes).count()
        porcentaje = (casos_filtrados / total_casos * 100) if total_casos > 0 else 0

        if matriz.alcances_utilizados=='A':
            alcance="MVP (Minimum Viable Product:A)"
        elif matriz.alcances_utilizados=='A,B':
            alcance='Smoke Test (A,B)'
        elif matriz.alcances_utilizados=='A,B,C':
            alcance='No Afectacion (NA:A,B,C)'
        else:
            alcance = 'No definido'

        # Construir dict de testers por región basado en tu campo antiguo "tester"
        testers_por_region = defaultdict(set)
        for caso in casos:
            if caso.tester:
                partes = caso.tester.split('-')
                if len(partes) == 2:
                    nombre, region = partes
                    testers_por_region[region.strip()].add(nombre.strip())
        
        testers_por_region = {region: sorted(list(nombres)) for region, nombres in testers_por_region.items()}

        # Indicador si hay testers asignados en los casos (tester_asignado)
        tiene_testers_asignados = casos.filter(tester_asignado__isnull=False).exists()

        matrices_info.append({
            'matriz': matriz,
            'total_casos': total_casos,
            'casos_filtrados': casos_filtrados,
            'porcentaje': round(porcentaje, 2),
            'testers_por_region': testers_por_region,
            'alcance': alcance,
            'dispositivo': matriz.dispositivo,
            'tiene_testers_asignados': tiene_testers_asignados
        })

    return matrices_info
def matriz_fails(matriz):
    matrices_fails = []
    
    casos = matriz.casos.all()
    estados_interes = ['falla_nueva', 'falla_persistente']
    casos_filtrados = casos.filter(criticidad__iexact='Bloqueante',estado__in=estados_interes)
    matrices_fails.append({
            'matriz': matriz,
            'casos_filtrados': casos_filtrados,
            'interes':estados_interes,
            'indice':casos_filtrados.count()
    })

    return matrices_fails
def matrices_fails(matrices):
    matrices_fails = []
    for matriz in matrices:
        matrices_fails.append(
            matriz_fails(matriz)
        )
    return matrices_fails
def obtener_testers_por_region_unicos(matrices):
    testers_por_matriz = {}

    for matriz in matrices:
        testers_por_region = {}

        for caso in matriz.casos.all():
            if caso.tester_asignado and caso.pais:
                region = caso.pais.strip()
                tester = caso.tester_asignado.nombre.strip()

                if region not in testers_por_region:
                    testers_por_region[region] = set()

                testers_por_region[region].add(tester)

        # Convertimos los sets en listas ordenadas para no repetir
        testers_por_matriz[matriz.id] = {
            region: sorted(list(testers))
            for region, testers in testers_por_region.items()
        }

    return testers_por_matriz

# Función para obtener testers a mostrar
def obtener_testers(matriz):
    testers_mostrar = []
    for caso in matriz.casos.all():
        if caso.tester:
            testers_mostrar.append({
                'tester': caso.tester,
                'pais': caso.pais  # puede ser None
            })
    if testers_mostrar:
        # Eliminamos duplicados manteniendo orden
        seen = set()
        unique_testers = []
        for t in testers_mostrar:
            key = (t['tester'], t['pais'])
            if key not in seen:
                seen.add(key)
                unique_testers.append(t)
        return unique_testers

    # Si no hay testers en los casos, usamos tester_asignado
    from collections import defaultdict
    region_dict = defaultdict(set)
    for caso in matriz.casos.all():
        if caso.tester_asignado:
            pais = caso.pais if caso.pais else None
            region_dict[pais].add(caso.tester_asignado.nombre)

    for pais, testers in region_dict.items():
        for tester in sorted(testers):
            testers_mostrar.append({'tester': tester, 'pais': pais})

    return testers_mostrar


def obtener_informacion_matriz(matriz_id):
    """
    Obtiene información completa de una matriz incluyendo conteo de casos bloqueantes, porcentaje de avance y países únicos
    """
    try:
        matriz = Matriz.objects.select_related('dispositivo').prefetch_related('testers').get(id=matriz_id)
        
        # Obtener todos los casos de la matriz
        casos = matriz.casos.all()
        total_casos = casos.count()
        
        # Filtro CORREGIDO con estados específicos para casos bloqueantes
        casos_bloqueantes_filtrados = casos.filter(
            criticidad='Bloqueante',
            estado__in=['falla_persistente', 'falla_nueva']
        )
        
        # Calcular porcentaje de avance
        estados_interes = ['funciona', 'falla_nueva', 'falla_persistente', "na","pendiente_por_externo"]
        casos_filtrados = casos.filter(estado__in=estados_interes).count()
        porcentaje = (casos_filtrados / total_casos * 100) if total_casos > 0 else 0
        
        # Obtener información de testers
        testers_info = list(matriz.testers.values('id', 'nombre', 'apellido'))
        
        # Obtener países únicos - PRIMERO de campo pais
        paises_directos = casos.exclude(pais__isnull=True).exclude(pais__exact='').values_list('pais', flat=True).distinct()
        
        # Obtener países del campo tester (cuando pais está vacío)
        paises_de_tester = casos.filter(
            Q(pais__isnull=True) | Q(pais__exact=''),  # Donde pais está vacío
            tester__isnull=False,  # Y tester no es nulo
            tester__contains='-'   # Y tester contiene guión
        ).annotate(
            pais_extract=F('tester')  # Aquí extraeríamos la parte después del guión
        )
        
        # Procesar para extraer países del campo tester
        paises_set = set()
        
        # Agregar países directos
        for pais in paises_directos:
            if pais and pais.strip():
                paises_set.add(pais.strip())
        
        # Agregar países extraídos del campo tester
        for caso in paises_de_tester:
            if caso.tester and caso.tester.strip():
                tester_text = caso.tester.strip()
                if '-' in tester_text:
                    partes = tester_text.split('-')
                    if len(partes) > 1:
                        pais_extract = partes[-1].strip()
                        if pais_extract:
                            paises_set.add(pais_extract)
        
        # Convertir a lista y ordenar alfabéticamente
        paises_lista = sorted(list(paises_set))
        
        return {
            'nombre': matriz.nombre,
            'fecha_creacion': matriz.fecha_creacion,
            'alcance': matriz.alcances_utilizados,
            'dispositivo': matriz.dispositivo.nombre if matriz.dispositivo else None,
            'testers': testers_info,
            'casos_bloqueantes': casos_bloqueantes_filtrados.count(),
            'porcentaje': round(porcentaje, 2),
            'total_casos': total_casos,  # Para referencia
            'casos_ejecutados': casos_filtrados,  # Para referencia
            'paises': paises_lista  # Lista de países únicos
        }
        
    except Matriz.DoesNotExist:
        return None
    except Exception as e:
        print(f"Error obteniendo información de matriz: {e}")
        return None
def obtener_matrices_por_supermatriz(supermatriz_id):
    """
    Obtiene todas las matrices de una supermatriz con su información completa
    
    Args:
        supermatriz_id (int): ID de la supermatriz
    
    Returns:
        list: Lista de diccionarios con información de cada matriz
    """
    try:
        from .models import SuperMatriz
        
        # Verificar que la supermatriz existe
        supermatriz = SuperMatriz.objects.get(id=supermatriz_id)
        
        # Obtener todas las matrices de esta supermatriz
        matrices_ids = supermatriz.matrices.values_list('id', flat=True)
        
        # Usar la función anterior para obtener información de cada matriz
        matrices_info = []
        for matriz_id in matrices_ids:
            info_matriz = obtener_informacion_matriz(matriz_id)
            if info_matriz:
                # Agregar el ID de la matriz a la información
                info_matriz['id'] = matriz_id
                matrices_info.append(info_matriz)
        
        return {
            'supermatriz_nombre': supermatriz.nombre,
            'matrices': matrices_info,
        }
        
    except SuperMatriz.DoesNotExist:
        return None
    except Exception as e:
        print(f"Error obteniendo matrices de supermatriz: {e}")
        return None
def obtener_supermatrices_por_equipo_con_filtros(equipo_id, solo_activas=True):
    """
    Obtiene supermatrices por equipo con filtros adicionales
    
    Args:
        equipo_id (int): ID del equipo
        solo_activas (bool): Si True, solo retorna supermatrices no archivadas
    
    Returns:
        list: Lista de supermatrices filtradas
    """
    try:
        
        
        equipo = Equipo.objects.get(id=equipo_id)
        
        # Query base
        supermatrices = SuperMatriz.objects.filter(equipo_nuevo_id=equipo_id)
        
        # Aplicar filtro de archivado si se solicita
        if solo_activas:
            supermatrices = supermatrices.filter(archivado=False)
        
        supermatrices = supermatrices.order_by('-fecha_creacion')
        
        supermatrices_info = []
        for supermatriz in supermatrices:
            supermatrices_info.append({
                'id': supermatriz.id,
                'nombre': supermatriz.nombre,
                'descripcion': supermatriz.descripcion,
                'fecha_creacion': supermatriz.fecha_creacion,
                'fecha_fin': supermatriz.fecha_fin,
                'cantidad_matrices': supermatriz.matrices.count()
            })
        
        return {
            'equipo_nombre': equipo.nombre,
            'supermatrices': supermatrices_info,
            'total_supermatrices': len(supermatrices_info),
        }
        
    except Equipo.DoesNotExist:
        return None
def obtener_todos_los_equipos_completo(solo_activas=True):
    """
    Obtiene todos los equipos con todas sus supermatrices y matrices completas
    
    Args:
        solo_activas (bool): Si True, solo retorna supermatrices no archivadas
    
    Returns:
        list: Lista de equipos con toda su información anidada
    """
    try:
        equipos = Equipo.objects.all().order_by('nombre')
        
        equipos_completos = []
        
        for equipo in equipos:
            # Obtener supermatrices del equipo
            resultado_equipo = obtener_supermatrices_por_equipo_con_filtros(equipo.id, solo_activas)
            
            if resultado_equipo:
                equipo_info = {
                    'id': equipo.id,
                    'nombre': equipo.nombre,
                    'supermatrices': []
                }
                
                # Para cada supermatriz, obtener sus matrices completas
                for supermatriz in resultado_equipo['supermatrices']:
                    # Obtener matrices de esta supermatriz
                    matrices_resultado = obtener_matrices_por_supermatriz(supermatriz['id'])
                    
                    supermatriz_completa = {
                        **supermatriz,
                        'matrices_detalladas': matrices_resultado['matrices'] if matrices_resultado else []
                    }
                    
                    equipo_info['supermatrices'].append(supermatriz_completa)
                
                equipos_completos.append(equipo_info)
        
        return {
            'total_equipos': len(equipos_completos),
            'equipos': equipos_completos
        }
        
    except Exception as e:
        print(f"Error obteniendo todos los equipos completos: {e}")
        return None


def distribuir_casos_equitativamente(matriz, testers_seleccionados, regiones_seleccionadas):
    """
    Distribuye los casos de manera equitativa entre testers y regiones,
    evitando duplicaciones y asegurando distribución balanceada.
    Si hay igual cantidad de testers y regiones, asigna una región por tester.
    """
    if not testers_seleccionados or not regiones_seleccionadas:
        return

    # Obtener todos los casos de la matriz
    casos = list(matriz.casos.all())
    total_casos = len(casos)
    
    if total_casos == 0:
        return

    # Calcular distribución óptima
    total_testers = len(testers_seleccionados)
    total_regiones = len(regiones_seleccionadas)
    
    # CASO ESPECIAL: Misma cantidad de testers y regiones
    if total_testers == total_regiones:
        # Asignar una región diferente a cada tester
        for i, tester in enumerate(testers_seleccionados):
            region = regiones_seleccionadas[i]
            
            # Calcular cuántos casos corresponden a este tester
            casos_por_tester = total_casos // total_testers
            casos_extra = total_casos % total_testers
            
            # Determinar índices de casos para este tester
            inicio = i * casos_por_tester + min(i, casos_extra)
            fin = inicio + casos_por_tester + (1 if i < casos_extra else 0)
            
            # Asignar los casos a este tester y su región asignada
            for j in range(inicio, fin):
                if j < total_casos:
                    caso = casos[j]
                    caso.tester_asignado = tester
                    caso.pais = region
                    caso.save()
    
    # CASO NORMAL: Funcionalidad original (todas las combinaciones tester-región)
    else:
        # Crear combinaciones únicas de tester-región
        combinaciones = []
        for tester in testers_seleccionados:
            for region in regiones_seleccionadas:
                combinaciones.append((tester, region))
        
        # Mezclar las combinaciones para distribución aleatoria pero equitativa
        random.shuffle(combinaciones)
        
        # Calcular casos por combinación
        casos_por_combinacion = total_casos // len(combinaciones)
        casos_extra = total_casos % len(combinaciones)
        
        # Distribuir casos
        caso_index = 0
        
        for i, (tester, region) in enumerate(combinaciones):
            # Calcular cuántos casos asignar a esta combinación
            casos_a_asignar = casos_por_combinacion
            if i < casos_extra:
                casos_a_asignar += 1
            
            # Asignar casos a esta combinación tester-región
            for j in range(casos_a_asignar):
                if caso_index < total_casos:
                    caso = casos[caso_index]
                    caso.tester_asignado = tester
                    caso.pais = region
                    caso.save()
                    caso_index += 1
        
        # Si aún quedan casos por asignar (por redondeo), distribuirlos equitativamente
        if caso_index < total_casos:
            combinaciones_restantes = combinaciones[:]
            random.shuffle(combinaciones_restantes)
            
            for caso in casos[caso_index:]:
                if not combinaciones_restantes:
                    combinaciones_restantes = combinaciones.copy()
                    random.shuffle(combinaciones_restantes)
                
                tester, region = combinaciones_restantes.pop()
                caso.tester_asignado = tester
                caso.pais = region
                caso.save()