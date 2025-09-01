import openpyxl
from .models import CasoDePrueba,Validate
from requests.auth import HTTPBasicAuth
from decouple import config
from collections import defaultdict
import pandas as pd
import re
import requests
import random
import os


JIRA_EMAIL,JIRA_API_TOKEN = os.getenv('JIRA_EMAIL'),os.getenv('JIRA_API_TOKEN')
print(JIRA_API_TOKEN,JIRA_EMAIL)
def limpiar(valor):
    if isinstance(valor, str):
        return valor.strip()
    return valor

import openpyxl
from .models import CasoDePrueba


def importar_matriz_desde_excel(matriz, ruta_excel, alcances_permitidos=None):
    """
    Importa casos de prueba desde un archivo Excel y los asigna a una matriz.
    Filtra por alcance si se proporciona una lista de alcances_permitidos (['A', 'B', 'C']).
    Las filas incompletas (sin alcance, fase, caso o criticidad) se ignoran.
    """
    wb = openpyxl.load_workbook(ruta_excel)
    sheet = wb.active

    for fila in sheet.iter_rows(min_row=2, values_only=True):
        alcance = fila[0]
        fase = fila[1]
        caso_de_prueba = fila[2]
        criticidad = fila[4]
        nota = fila[5] if len(fila) > 5 else ""

        # Validar que los campos clave no estén vacíos
        if not (alcance and fase and caso_de_prueba and criticidad):
            continue  # Ignorar la fila si falta alguno

        # Filtrar por alcance si se especifica
        if alcances_permitidos and alcance not in alcances_permitidos:
            continue

        # Crear el caso de prueba
        CasoDePrueba.objects.create(
            matriz=matriz,
            alcance=alcance,
            fase=fase,
            caso_de_prueba=caso_de_prueba,
            estado="por_ejecutar",
            criticidad=criticidad,
            nota=nota or ""
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
def fetch_jira_issues(link):
    """
    Obtiene todos los issues desde Jira usando un link de filtro.
    """
    import json

    match = re.search(r'filter=(\d+)', link)
    if not match:
        return None, "No se pudo extraer el filtro del enlace."

    filter_id = match.group(1)
    headers = {"Accept": "application/json"}

    try:
        # Obtener JQL del filtro
        filter_url = f"https://dlatvarg.atlassian.net/rest/api/3/filter/{filter_id}"
        filter_response = requests.get(
            filter_url,
            headers=headers,
            auth=HTTPBasicAuth(config('JIRA_EMAIL'), config('JIRA_API_TOKEN'))
        )
        filter_response.raise_for_status()
        filter_data = filter_response.json()
        jql = filter_data.get('jql')
        if not jql:
            return None, "No se pudo obtener el JQL del filtro."

        # Traer todos los issues con paginación
        search_url = "https://dlatvarg.atlassian.net/rest/api/3/search/jql"
        start_at = 0
        max_results = 50
        all_issues = []

        while True:
            params = {'jql': jql, 'startAt': start_at, 'maxResults': max_results}
            response = requests.get(
                search_url,
                headers=headers,
                params=params,
                auth=HTTPBasicAuth(config('JIRA_EMAIL'), config('JIRA_API_TOKEN'))
            )
            response.raise_for_status()
            data = response.json()

            issues = data.get('issues', [])
            for issue in issues:
                key = issue.get('key')
                fields = issue.get('fields', {})
                summary = fields.get('summary')
                description = fields.get('description', 'Sin descripción')
                priority = fields.get('priority', {}).get('name', 'Sin prioridad')

                if key:
                    all_issues.append({
                        'key': key,
                        'summary': summary,
                        'description': description,
                        'priority': priority
                    })

            # Revisar si hay más issues
            if start_at + max_results >= data.get('total', 0):
                break
            start_at += max_results

    except requests.RequestException as e:
        return None, f"Error al obtener issues: {e}"
    except json.JSONDecodeError:
        return None, "No se pudo decodificar la respuesta de Jira."

    if not all_issues:
        return None, "No se encontraron issues."

    return all_issues, None

def matriz_info(matrices):
    matrices_info = []
    for matriz in matrices:
        casos = matriz.casos.all()
        total_casos = casos.count()
        estados_interes = ['funciona', 'falla_nueva', 'falla_persistente', "na"]
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

        testers_por_region = defaultdict(set)
        for caso in casos:
            if caso.tester:
                partes = caso.tester.split('-')
                if len(partes) == 2:
                    nombre, region = partes
                    testers_por_region[region.strip()].add(nombre.strip())

        testers_por_region = {region: sorted(list(nombres)) for region, nombres in testers_por_region.items()}

        matrices_info.append({
            'matriz': matriz,
            'total_casos': total_casos,
            'casos_filtrados': casos_filtrados,
            'porcentaje': round(porcentaje, 2),
            'testers_por_region': testers_por_region,
            'alcance': alcance,
            'dispositivo': matriz.dispositivo,  
        })

    return matrices_info
    
