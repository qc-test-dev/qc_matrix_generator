import os
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import random
from main_website import settings
from .forms import (
    SuperMatrizForm, MatrizForm, CasoDePruebaForm,
    ValidateEstadoForm, DetallesValidateForm,
    TicketPorLevantarForm, ValidateForm, SuperMatrizFechaFinForm,
    SuperMatrizDescripcionForm, FeatureUploadForm
)
from .models import SuperMatriz, Matriz, Validate, TicketPorLevantar, DetallesValidate, Dispositivo, Equipo, FeatureFile, FeatureScenario
from .utils import importar_matriz_desde_excel,importar_validates,matriz_info,matriz_fails,obtener_matrices_por_supermatriz,obtener_supermatrices_por_equipo_con_filtros,obtener_todos_los_equipos_completo,obtener_informacion_matriz,distribuir_casos_equitativamente
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model
from app.accounts.models import User
from collections import defaultdict
Usuario = get_user_model()
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from collections import defaultdict
import random
import os
from django.contrib import messages
from django.conf import settings
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.http import JsonResponse
from .models import CasoDePrueba

from .models import SuperMatriz, Validate
from .forms import MatrizForm, ValidateForm
from .utils import importar_matriz_desde_excel
from django.views.decorators.csrf import csrf_exempt
from app.matrix.models import SuperMatriz, Dispositivo
from collections import defaultdict
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from weasyprint import HTML
from django.template.loader import render_to_string
from datetime import datetime
from django.utils.timezone import localtime
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import locale, json
import re
locale.setlocale(locale.LC_TIME, 'es_MX.UTF-8')
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import SuperMatriz, Matriz
from .forms import MatrizForm, ValidateForm
from django.utils import timezone
import os
import random
import csv


def _parse_feature_scenarios(feature_text: str):
    """
    Parser Gherkin: extrae el nombre del Feature, Scenario/Scenario Outline,
    tags y las líneas de pasos (Given/When/Then, etc.) por escenario.
    Devuelve {'feature_name': str, 'scenarios': list}.
    """
    feature_name = ""
    scenarios = []
    current_tags = []
    lines = feature_text.splitlines()

    i = 0
    while i < len(lines):
        raw_line = lines[i]
        line = raw_line.strip()
        idx = i + 1  # 1-based line number

        if not line:
            i += 1
            continue

        # Nombre del Feature (línea "Feature: ...")
        if line.lower().startswith('feature'):
            if ':' in line:
                feature_name = line.split(':', 1)[1].strip()
            i += 1
            continue

        # Tags
        if line.startswith('@'):
            current_tags = line.split()
            i += 1
            continue

        # Scenario / Scenario Outline
        if line.lower().startswith('scenario'):
            nombre = line  # "Scenario: ..." o "Scenario Outline: ..."
            tags_str = ' '.join(current_tags)
            # Recoger pasos: líneas siguientes hasta otro Scenario o bloque de tags
            step_lines = []
            j = i + 1
            while j < len(lines):
                next_raw = lines[j]
                next_stripped = next_raw.strip()
                if next_stripped.lower().startswith('scenario'):
                    break
                if next_stripped.startswith('@'):
                    break
                if next_stripped.lower().startswith('feature'):
                    break
                if next_stripped:
                    step_lines.append(next_raw.rstrip())
                j += 1
            steps_text = '\n'.join(step_lines)
            is_outline = 'scenario outline' in line.lower()
            scenarios.append({
                'nombre': nombre,
                'linea': idx,
                'tags': tags_str,
                'steps': steps_text,
                'is_outline': is_outline,
            })
            current_tags = []
            i = j
            continue
        i += 1

    return {'feature_name': feature_name or 'Feature', 'scenarios': scenarios}


def sync_scenarios_from_featurefile(feature_file: FeatureFile):
    """
    Lee el .feature físico, recalcula SHA, y sincroniza los FeatureScenario:
    - crea nuevos escenarios
    - actualiza nombre/linea/tags
    - conserva estado/observaciones
    - elimina escenarios que ya no existen
    """
    path = feature_file.get_feature_path()
    if not path or not os.path.exists(path):
        return

    # Recalcular checksum
    feature_file.recalcular_sha256()
    feature_file.save(update_fields=['sha256', 'actualizado_en'])

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    parsed = _parse_feature_scenarios(content)
    feature_name = parsed.get('feature_name') or 'Feature'
    parsed_scenarios = parsed.get('scenarios', [])

    # Sincronizar modelos FeatureScenario (estado/observaciones por escenario)
    existentes = {
        s.stable_id: s
        for s in feature_file.scenarios.all()
    }
    vistos = set()

    for data in parsed_scenarios:
        nombre = data['nombre']
        linea = data['linea']
        tags = data['tags']
        stable_id = FeatureScenario.build_stable_id(nombre, linea)
        vistos.add(stable_id)

        if stable_id in existentes:
            s = existentes[stable_id]
            s.nombre = nombre
            s.linea = linea
            s.tags = tags
            s.save(update_fields=['nombre', 'linea', 'tags', 'sincronizado_en'])
        else:
            FeatureScenario.objects.create(
                feature_file=feature_file,
                stable_id=stable_id,
                nombre=nombre,
                linea=linea,
                tags=tags,
            )

    # Eliminar escenarios que ya no existen en el archivo
    for stable_id, s in existentes.items():
        if stable_id not in vistos:
            s.delete()

    # Además, si este feature está ligado a una Matriz, sincronizar también CasoDePrueba
    matriz = feature_file.matriz
    if matriz:
        from .models import CasoDePrueba  # import local para evitar ciclos al cargar módulos

        # stable_id incluye feature_file.id para soportar varios .feature por matriz
        def caso_stable_id(nombre_escenario: str, linea_esc: int) -> str:
            base = FeatureScenario.build_stable_id(nombre_escenario, linea_esc)
            return f"{feature_file.id}-{base}"

        # Solo casos que pertenecen a este feature_file (por prefijo de stable_id)
        prefix = f"{feature_file.id}-"
        casos_existentes = {
            c.scenario_stable_id: c
            for c in matriz.casos.all()
            if c.scenario_stable_id and c.scenario_stable_id.startswith(prefix)
        }
        casos_vistos = set()

        # Longitud máxima de pasos en CasoDePrueba (CharField)
        PASOS_MAX_LEN = 700
        fase_val = (feature_name or '')[:50]

        def _summary_from_csv_row(row, scenario_nombre):
            """Resumen corto para caso_de_prueba a partir de la fila CSV."""
            if not row:
                return scenario_nombre[:200]
            if 'addon' in row:
                addon = row.get('addon', '')
                mdp = row.get('type_MDP', '')
                return f"{scenario_nombre[:35]} | {addon} ({mdp})"[:500]
            parts = [f"{k}={v}" for k, v in list(row.items())[:4]]
            return f"{scenario_nombre[:30]} | {', '.join(parts)}"[:500]

        def _read_csv_rows(csv_path):
            """Lee CSV y devuelve lista de dicts (una por fila); salta filas vacías."""
            rows = []
            try:
                with open(csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f, skipinitialspace=True)
                    for r in reader:
                        if not r or all(not str(v).strip() for v in r.values()):
                            continue
                        rows.append({k.strip(): v.strip() if v else '' for k, v in r.items()})
            except Exception:
                pass
            return rows

        for data in parsed_scenarios:
            nombre = data['nombre']
            linea = data['linea']
            steps = data.get('steps', '') or ''
            if len(steps) > PASOS_MAX_LEN:
                steps = steps[: PASOS_MAX_LEN - 3] + '...'
            is_outline = data.get('is_outline', False)
            csv_path = feature_file.get_csv_path() if feature_file.has_csv() else None

            if is_outline and csv_path and os.path.exists(csv_path):
                # Scenario Outline + CSV: un caso de prueba por fila del CSV
                csv_rows = _read_csv_rows(csv_path)
                for row_idx, row in enumerate(csv_rows):
                    stable_id = f"{feature_file.id}-outline-{linea}-row-{row_idx}"
                    casos_vistos.add(stable_id)
                    summary = _summary_from_csv_row(row, nombre)
                    if stable_id in casos_existentes:
                        caso = casos_existentes[stable_id]
                        caso.caso_de_prueba = summary
                        caso.fase = fase_val
                        caso.pasos = steps
                        caso.datos_examples = row
                        caso.save(update_fields=['caso_de_prueba', 'fase', 'pasos', 'datos_examples'])
                    else:
                        CasoDePrueba.objects.create(
                            matriz=matriz,
                            alcance='A',
                            fase=fase_val,
                            caso_de_prueba=summary,
                            estado='por_ejecutar',
                            criticidad='Crítico',
                            scenario_stable_id=stable_id,
                            pasos=steps,
                            datos_examples=row,
                        )
            else:
                # Scenario normal o Scenario Outline sin CSV: un caso por escenario
                stable_id = caso_stable_id(nombre, linea)
                casos_vistos.add(stable_id)
                if stable_id in casos_existentes:
                    caso = casos_existentes[stable_id]
                    caso.caso_de_prueba = nombre
                    caso.fase = fase_val
                    caso.pasos = steps
                    if getattr(caso, 'datos_examples', None) is not None:
                        caso.datos_examples = None
                        caso.save(update_fields=['caso_de_prueba', 'fase', 'pasos', 'datos_examples'])
                    else:
                        caso.save(update_fields=['caso_de_prueba', 'fase', 'pasos'])
                else:
                    CasoDePrueba.objects.create(
                        matriz=matriz,
                        alcance='A',
                        fase=fase_val,
                        caso_de_prueba=nombre,
                        estado='por_ejecutar',
                        criticidad='Crítico',
                        scenario_stable_id=stable_id,
                        pasos=steps,
                    )

        # Eliminar casos que ya no correspondan a ningún escenario/fila de este .feature
        for stable_id, caso in casos_existentes.items():
            if stable_id not in casos_vistos:
                caso.delete()


@login_required
def detalle_super_matriz(request, super_matriz_id):
    super_matriz = get_object_or_404(SuperMatriz, id=super_matriz_id)
    validates = super_matriz.validates.all()
    es_lider = request.user.cargo == 'Lider'
    equipo_nuevo = getattr(super_matriz, 'equipo_nuevo', super_matriz.equipo)

    # OBTENER INFORMACIÓN OPTIMIZADA usando la función
    supermatriz_info = obtener_matrices_por_supermatriz(super_matriz_id)
    
    # Si no hay información, crear estructura vacía
    if not supermatriz_info:
        supermatriz_info = {
            'supermatriz_nombre': super_matriz.nombre,
            'matrices': []
        }

    # CALCULAR LOS TOTALES REQUERIDOS
    matrices = supermatriz_info['matrices']
    
    # Total de matrices
    total_matrices = len(matrices)
    
    # Sumar todos los casos totales
    total_casos = sum(matriz.get('total_casos', 0) for matriz in matrices)
    
    # Sumar todos los casos ejecutados
    casos_ejecutados = sum(matriz.get('casos_ejecutados', 0) for matriz in matrices)
    
    # Sumar todos los casos bloqueantes
    casos_bloqueantes = sum(matriz.get('casos_bloqueantes', 0) for matriz in matrices)
    
    # Calcular porcentaje promedio de avance
    if total_matrices > 0:
        porcentajes = [matriz.get('porcentaje', 0) for matriz in matrices]
        porcentaje_promedio = sum(porcentajes) / total_matrices
    else:
        porcentaje_promedio = 0

    # Mantener la lógica original para testers y fallas
    def obtener_testers(matriz_obj):
        testers_mostrar = []
        for caso in matriz_obj.casos.all():
            if caso.tester:
                testers_mostrar.append({
                    'tester': caso.tester,
                    'pais': caso.pais
                })
        if testers_mostrar:
            seen = set()
            unique_testers = []
            for t in testers_mostrar:
                key = (t['tester'], t['pais'])
                if key not in seen:
                    seen.add(key)
                    unique_testers.append(t)
            return unique_testers

        from collections import defaultdict
        region_dict = defaultdict(set)
        for caso in matriz_obj.casos.all():
            if caso.tester_asignado:
                pais = caso.pais if caso.pais else None
                region_dict[pais].add(caso.tester_asignado.nombre)

        for pais, testers in region_dict.items():
            for tester in sorted(testers):
                testers_mostrar.append({'tester': tester, 'pais': pais})

        return testers_mostrar

    # Crear matrices_info compatible con el template original
    matrices_info = []
    for matriz_data in supermatriz_info['matrices']:
        # Obtener el objeto matriz original
        matriz_obj = Matriz.objects.get(id=matriz_data['id'])
        casos_externos = matriz_obj.casos.all().filter(estado__in=['pendiente_por_externo']).count()
        # Obtener información de fallas
        fallas_info = matriz_fails(matriz_obj)
        if fallas_info:
            fallas_data = fallas_info[0]
        else:
            fallas_data = {'indice': 0, 'casos_filtrados': []}
        
        # Construir la estructura que espera el template
        matriz_info_item = {
            'matriz': matriz_obj,
            'dispositivo': matriz_obj.dispositivo,
            'alcance': matriz_data.get('alcance', ''),
            'total_casos': matriz_data.get('total_casos', 0),
            'casos_filtrados': matriz_data.get('casos_ejecutados', 0),
            'porcentaje': matriz_data.get('porcentaje', 0),
            'testers_mostrar': obtener_testers(matriz_obj),
            'fallas': fallas_data,
            'externos': casos_externos
        }
        matrices_info.append(matriz_info_item)

    form = MatrizForm(equipo_nuevo=equipo_nuevo)
    validate_form = ValidateForm()

    if request.method == 'POST':
        if 'crear_matriz' in request.POST:
            form = MatrizForm(request.POST, equipo_nuevo=equipo_nuevo)
            if form.is_valid():
                nueva_matriz = form.save(commit=False)
                nueva_matriz.super_matriz = super_matriz

                alcance_seleccionado = request.POST.get('alcance', '')
                valores_a_incluir = set(alcance_seleccionado.split(',')) if alcance_seleccionado else set()
                nueva_matriz.alcances_utilizados = ",".join(sorted(valores_a_incluir))
                nueva_matriz.save()

                testers_seleccionados = list(form.cleaned_data.get('testers', []))
                if testers_seleccionados:
                    nueva_matriz.testers.set(testers_seleccionados)

                dispositivo = form.cleaned_data.get('dispositivo')
                if not dispositivo or not dispositivo.matriz_base:
                    messages.error(request, f"El dispositivo no tiene archivo base asociado.")
                    return redirect('matrix_app:detalle_super_matriz', super_matriz_id=super_matriz.id)

                # ====== CAMBIO AQUÍ ======
                # Buscar el archivo en media/excel/{nombre_equipo}/{matriz_base}
                nombre_equipo = dispositivo.equipo.nombre.replace(' ', '_')
                nombre_archivo = dispositivo.matriz_base
                
                # Ruta nueva: media/excel/{nombre_equipo}/{nombre_archivo}
                ruta_excel_matriz = os.path.join(
                    settings.MEDIA_ROOT, 
                    'excel', 
                    nombre_equipo, 
                    nombre_archivo
                )
                
                # Verificar si el archivo existe
                if not os.path.exists(ruta_excel_matriz):
                    # También podríamos intentar con el campo archivo_excel.url si existe
                    if hasattr(dispositivo, 'archivo_excel') and dispositivo.archivo_excel:
                        ruta_excel_matriz = dispositivo.archivo_excel.path
                        
                        if not os.path.exists(ruta_excel_matriz):
                            messages.error(request, f"El archivo '{nombre_archivo}' no existe en la ruta: {ruta_excel_matriz}")
                            return redirect('matrix_app:detalle_super_matriz', super_matriz_id=super_matriz.id)
                    else:
                        messages.error(request, f"El archivo '{nombre_archivo}' no existe en el servidor.")
                        return redirect('matrix_app:detalle_super_matriz', super_matriz_id=super_matriz.id)
                # ====== FIN DEL CAMBIO ======

                # LLAMAR A LA FUNCIÓN MODIFICADA QUE RETORNA (success, error_message)
                success, mensaje = importar_matriz_desde_excel(nueva_matriz, ruta_excel_matriz, valores_a_incluir)
                
                if not success:
                    # Si hay error, eliminar la matriz creada y mostrar mensaje
                    nueva_matriz.delete()
                    messages.error(request, mensaje)
                    return redirect('matrix_app:detalle_super_matriz', super_matriz_id=super_matriz.id)

                regiones_seleccionadas = form.cleaned_data.get('regiones', [])
                # MEJORA: Distribución equitativa de casos
                distribuir_casos_equitativamente(nueva_matriz, testers_seleccionados, regiones_seleccionadas)

                messages.success(request, "Matriz creada correctamente.")
                return redirect('matrix_app:detalle_super_matriz', super_matriz_id=super_matriz.id)

        elif 'crear_validate' in request.POST:
            validate_form = ValidateForm(request.POST)
            if validate_form.is_valid():
                validate = validate_form.save(commit=False)
                validate.super_matriz = super_matriz
                validate.save()
                messages.success(request, "Validate creado correctamente.")
                return redirect('matrix_app:detalle_super_matriz', super_matriz_id=super_matriz.id)

    return render(request, 'excel_files/detalle_super_matriz.html', {
        'super_matriz': super_matriz,
        'matrices_info': matrices_info,
        'form': form,
        'validate_form': validate_form,
        'validates': validates,
        'es_lider': es_lider,
        'equipo_nuevo': equipo_nuevo,
        # NUEVOS DATOS PARA EL RESUMEN
        'porcentaje_promedio': porcentaje_promedio,
        'total_casos': total_casos,
        'casos_ejecutados': casos_ejecutados,
        'casos_bloqueantes': casos_bloqueantes,
    })


@login_required
def detalle_matriz(request, matriz_id):
    matriz = get_object_or_404(Matriz, id=matriz_id)
    super_matriz_id = matriz.super_matriz.id

    # Obtener parámetros de filtro desde la URL
    tester_filtrado = request.GET.get('tester')
    tester_asignado_filtrado = request.GET.get('tester_asignado')
    pais_filtrado = request.GET.get('pais')
    fallo_filtrado = request.GET.get('fallo')
    estado_filtrado = request.GET.get('estado')
    fase_filtrada = request.GET.get('fase')
    num_fallos = matriz_fails(matriz)[0]['indice']

    # Casos de prueba base
    casos_de_prueba = matriz.casos.all()

    # Aplicar filtros existentes (se mantienen igual)
    if tester_filtrado:
        casos_de_prueba = casos_de_prueba.filter(tester=tester_filtrado)

    if tester_asignado_filtrado and pais_filtrado:
        try:
            tester_id = int(tester_asignado_filtrado)
            casos_de_prueba = casos_de_prueba.filter(
                tester_asignado__id=tester_id,
                pais=pais_filtrado
            )
        except (ValueError, TypeError):
            casos_de_prueba = casos_de_prueba.filter(
                tester_asignado__nombre__icontains=tester_asignado_filtrado.split()[0],
                pais=pais_filtrado
            )
    elif tester_asignado_filtrado:
        try:
            tester_id = int(tester_asignado_filtrado)
            casos_de_prueba = casos_de_prueba.filter(
                tester_asignado__id=tester_id
            )
        except (ValueError, TypeError):
            casos_de_prueba = casos_de_prueba.filter(
                tester_asignado__nombre__icontains=tester_asignado_filtrado.split()[0]
            )
    elif pais_filtrado:
        casos_de_prueba = casos_de_prueba.filter(pais=pais_filtrado)

    # NUEVO: Aplicar filtro por fase si existe
    if fase_filtrada:
        casos_de_prueba = casos_de_prueba.filter(fase=fase_filtrada)

    # NUEVO: Aplicar filtro por estado si existe
    # Si el estado es "bloqueante", aplicar filtro especial de bloqueantes
    if estado_filtrado == 'bloqueante':
        # Filtrar casos bloqueantes (criticidad='Bloqueante' y estado en ['falla_nueva', 'falla_persistente'])
        casos_de_prueba = casos_de_prueba.filter(
            criticidad__iexact='Bloqueante',
            estado__in=['falla_nueva', 'falla_persistente']
        )
    elif estado_filtrado:
        casos_de_prueba = casos_de_prueba.filter(estado=estado_filtrado)

    # Ordenar los casos
    casos_de_prueba = casos_de_prueba.order_by("fase", "id")

    # Inicializar fallos para evitar errores
    fallos = []
    
    # Aplicar filtro de fallo usando la función matriz_fails (mantener compatibilidad con botón antiguo)
    # Solo aplicar si no se está usando estado=bloqueante (para evitar conflictos)
    if fallo_filtrado == 'bloqueante' and estado_filtrado != 'bloqueante':
        fallos = matriz_fails(matriz)
        casos_filtrados = fallos[0]['casos_filtrados']
        # Aplicar otros filtros al resultado de bloqueantes
        if fase_filtrada:
            casos_filtrados = casos_filtrados.filter(fase=fase_filtrada)
        if tester_filtrado:
            casos_filtrados = casos_filtrados.filter(tester=tester_filtrado)
        if tester_asignado_filtrado and pais_filtrado:
            try:
                tester_id = int(tester_asignado_filtrado)
                casos_filtrados = casos_filtrados.filter(
                    tester_asignado__id=tester_id,
                    pais=pais_filtrado
                )
            except (ValueError, TypeError):
                casos_filtrados = casos_filtrados.filter(
                    tester_asignado__nombre__icontains=tester_asignado_filtrado.split()[0],
                    pais=pais_filtrado
                )
        elif tester_asignado_filtrado:
            try:
                tester_id = int(tester_asignado_filtrado)
                casos_filtrados = casos_filtrados.filter(tester_asignado__id=tester_id)
            except (ValueError, TypeError):
                casos_filtrados = casos_filtrados.filter(
                    tester_asignado__nombre__icontains=tester_asignado_filtrado.split()[0]
                )
        elif pais_filtrado:
            casos_filtrados = casos_filtrados.filter(pais=pais_filtrado)
    else:
        casos_filtrados = casos_de_prueba

    # Formularios por caso
    formularios_casos_de_prueba = [
        (caso, CasoDePruebaForm(instance=caso, prefix=f"caso_{caso.id}"))
        for caso in casos_filtrados
    ]
    # Alcances
    if matriz.alcances_utilizados == 'A':
        alcance = "MVP (Minimum Viable Product:A)"
    elif matriz.alcances_utilizados == 'A,B':
        alcance = 'Smoke Test (A,B)'
    elif matriz.alcances_utilizados == 'A,B,C':
        alcance = 'No Afectacion (NA:A,B,C)'
    else:
        alcance = ''

    alcances_lista = matriz.alcances_utilizados.split(',') if matriz.alcances_utilizados else []

    # Testers disponibles (viejo - campo tester)
    testers_disponibles = list(
        matriz.casos.exclude(tester='').exclude(tester__isnull=True).values_list('tester', flat=True).distinct())

    ESTADOS_POSIBLES = [
        'funciona', 'falla_nueva', 'falla_persistente',
        'na', 'pendiente_por_qc', 'por_ejecutar', 'pendiente_por_externo'
    ]
    # Agregar "bloqueante" como opción especial en el dropdown
    estados_disponibles = ESTADOS_POSIBLES + ['bloqueante']
    fases_disponibles = list(matriz.casos.exclude(
        fase__isnull=True
    ).exclude(
        fase=''
    ).values_list('fase', flat=True).distinct().order_by('fase'))

    # Obtener los IDs de los testers asignados para filtrado preciso
    combinaciones_tester_pais = matriz.casos.exclude(
        tester_asignado__isnull=True
    ).exclude(
        pais__isnull=True
    ).exclude(
        pais=''
    ).values_list('tester_asignado__id', 'tester_asignado__nombre', 'tester_asignado__apellido', 'pais').distinct()

    botones_nuevos = []
    for tester_id, nombre, apellido, pais in combinaciones_tester_pais:
        nombre_completo = f"{nombre} {apellido}"
        texto_boton = f"{nombre_completo} - {pais}"
        botones_nuevos.append({
            'texto': texto_boton,
            'tester_id': tester_id,
            'tester_nombre': nombre_completo,
            'pais': pais
        })

    # Obtener testers asignados únicos (sin país)
    testers_asignados_unicos = matriz.casos.exclude(
        tester_asignado__isnull=True
    ).values_list('tester_asignado__id', 'tester_asignado__nombre', 'tester_asignado__apellido').distinct()
    
    testers_asignados_lista = []
    for tester_id, nombre, apellido in testers_asignados_unicos:
        nombre_completo = f"{nombre} {apellido}"
        testers_asignados_lista.append({
            'tester_id': tester_id,
            'tester_nombre': nombre_completo,
            'nombre_completo': nombre_completo
        })
    
    # Obtener países únicos
    paises_disponibles = list(matriz.casos.exclude(
        pais__isnull=True
    ).exclude(
        pais=''
    ).values_list('pais', flat=True).distinct().order_by('pais'))

    # Determinar qué botones mostrar
    mostrar_botones_viejos = len(testers_disponibles) > 0
    mostrar_botones_nuevos = len(botones_nuevos) > 0
    mostrar_tester_asignado = len(testers_asignados_lista) > 0
    mostrar_paises = len(paises_disponibles) > 0

    # determinar si hay datos en la matriz (etiqueta,tipo_usuario,pasos
    campos = {
        "etiqueta": casos_de_prueba.filter(etiqueta__isnull=False).exclude(etiqueta="").exists(),
        "tipo_usuario": casos_de_prueba.filter(tipo_usuario__isnull=False).exclude(tipo_usuario="").exists(),
        "pasos": casos_de_prueba.filter(pasos__isnull=False).exclude(pasos="").exists(),
        #"mdp": casos_de_prueba.filter(mdp__isnull=False).exclude(mdp="").exists(),
        #"monto": casos_de_prueba.filter(monto__isnull=False).exclude(monto="").exists(),
        #"navegador": casos_de_prueba.filter(navegador__isnull=False).exclude(navegador="").exists(),
    }

    # Crear lista de tuplas con (estado_original, estado_formateado)
    estados_combinados = []
    for estado in estados_disponibles:
        if estado == 'bloqueante':
            estado_formateado = '🛑 Bloqueante (Falla Nueva + Persistente)'
        else:
            estado_formateado = estado.replace('_', ' ').title()
        estados_combinados.append((estado, estado_formateado))

    # Formatear también el estado filtrado actual
    if estado_filtrado == 'bloqueante':
        estado_filtrado_formateado = '🛑 Bloqueante (Falla Nueva + Persistente)'
    elif estado_filtrado:
        estado_filtrado_formateado = estado_filtrado.replace('_', ' ').title()
    else:
        estado_filtrado_formateado = None

    # Crear parámetros de query string para mantener los filtros actuales
    # Si estado_filtrado es 'bloqueante', no incluir fallo_filtrado para evitar conflictos
    query_params = []

    if tester_filtrado:
        query_params.append(f"tester={tester_filtrado}")
    if tester_asignado_filtrado:
        query_params.append(f"tester_asignado={tester_asignado_filtrado}")
    if pais_filtrado:
        query_params.append(f"pais={pais_filtrado}")
    # Solo incluir fallo_filtrado si no estamos usando estado=bloqueante
    if fallo_filtrado and estado_filtrado != 'bloqueante':
        query_params.append(f"fallo={fallo_filtrado}")

    current_query_string = "&".join(query_params)
    has_other_filters = bool(current_query_string)
    
    # Crear query strings específicos para cada filtro (excluyendo el filtro que se está cambiando)
    query_params_sin_estado = []
    if tester_filtrado:
        query_params_sin_estado.append(f"tester={tester_filtrado}")
    if tester_asignado_filtrado:
        query_params_sin_estado.append(f"tester_asignado={tester_asignado_filtrado}")
    if pais_filtrado:
        query_params_sin_estado.append(f"pais={pais_filtrado}")
    if fase_filtrada:
        query_params_sin_estado.append(f"fase={fase_filtrada}")
    if fallo_filtrado and estado_filtrado != 'bloqueante':
        query_params_sin_estado.append(f"fallo={fallo_filtrado}")
    query_string_sin_estado = "&".join(query_params_sin_estado)
    
    query_params_sin_fase = []
    if tester_filtrado:
        query_params_sin_fase.append(f"tester={tester_filtrado}")
    if tester_asignado_filtrado:
        query_params_sin_fase.append(f"tester_asignado={tester_asignado_filtrado}")
    if pais_filtrado:
        query_params_sin_fase.append(f"pais={pais_filtrado}")
    if estado_filtrado:
        query_params_sin_fase.append(f"estado={estado_filtrado}")
    if fallo_filtrado and estado_filtrado != 'bloqueante':
        query_params_sin_fase.append(f"fallo={fallo_filtrado}")
    query_string_sin_fase = "&".join(query_params_sin_fase)
    
    query_params_sin_tester = []
    if estado_filtrado:
        query_params_sin_tester.append(f"estado={estado_filtrado}")
    if fase_filtrada:
        query_params_sin_tester.append(f"fase={fase_filtrada}")
    if tester_asignado_filtrado:
        query_params_sin_tester.append(f"tester_asignado={tester_asignado_filtrado}")
    if pais_filtrado:
        query_params_sin_tester.append(f"pais={pais_filtrado}")
    if fallo_filtrado and estado_filtrado != 'bloqueante':
        query_params_sin_tester.append(f"fallo={fallo_filtrado}")
    query_string_sin_tester = "&".join(query_params_sin_tester)
    
    query_params_sin_tester_asignado = []
    if estado_filtrado:
        query_params_sin_tester_asignado.append(f"estado={estado_filtrado}")
    if fase_filtrada:
        query_params_sin_tester_asignado.append(f"fase={fase_filtrada}")
    if tester_filtrado:
        query_params_sin_tester_asignado.append(f"tester={tester_filtrado}")
    if pais_filtrado:
        query_params_sin_tester_asignado.append(f"pais={pais_filtrado}")
    if fallo_filtrado and estado_filtrado != 'bloqueante':
        query_params_sin_tester_asignado.append(f"fallo={fallo_filtrado}")
    query_string_sin_tester_asignado = "&".join(query_params_sin_tester_asignado)
    
    query_params_sin_pais = []
    if estado_filtrado:
        query_params_sin_pais.append(f"estado={estado_filtrado}")
    if fase_filtrada:
        query_params_sin_pais.append(f"fase={fase_filtrada}")
    if tester_filtrado:
        query_params_sin_pais.append(f"tester={tester_filtrado}")
    if tester_asignado_filtrado:
        query_params_sin_pais.append(f"tester_asignado={tester_asignado_filtrado}")
    if fallo_filtrado and estado_filtrado != 'bloqueante':
        query_params_sin_pais.append(f"fallo={fallo_filtrado}")
    query_string_sin_pais = "&".join(query_params_sin_pais)

    return render(request, 'excel_files/detalle_matriz.html', {
        'matriz': matriz,
        'super_matriz_id': super_matriz_id,
        'alcances_lista': alcances_lista,
        'formularios_casos_de_prueba': formularios_casos_de_prueba,
        'testers_disponibles': testers_disponibles,
        'botones_nuevos': botones_nuevos,
        'tester_filtrado': tester_filtrado,
        'tester_asignado_filtrado': tester_asignado_filtrado,
        'pais_filtrado': pais_filtrado,
        'fallo_filtrado': fallo_filtrado,
        'alcance': alcance,
        'fallos': fallos if (fallo_filtrado == 'bloqueante' and estado_filtrado != 'bloqueante') or estado_filtrado == 'bloqueante' else [],
        'num_fallos': num_fallos,
        'mostrar_botones_viejos': mostrar_botones_viejos,
        'mostrar_botones_nuevos': mostrar_botones_nuevos,
        'campos': campos,
        # NUEVAS VARIABLES PARA LOS FILTROS
        'estados_combinados': estados_combinados,
        'fases_disponibles': fases_disponibles,
        'estado_filtrado': estado_filtrado,
        'estado_filtrado_formateado': estado_filtrado_formateado,
        'fase_filtrada': fase_filtrada,
        # NUEVAS VARIABLES PARA MANTENER FILTROS
        'current_query_string': current_query_string,
        'has_other_filters': has_other_filters,
        'query_string_sin_estado': query_string_sin_estado,
        'query_string_sin_fase': query_string_sin_fase,
        'query_string_sin_tester': query_string_sin_tester,
        'query_string_sin_tester_asignado': query_string_sin_tester_asignado,
        'query_string_sin_pais': query_string_sin_pais,
        # NUEVAS VARIABLES PARA DROPDOWNS SEPARADOS
        'testers_asignados_lista': testers_asignados_lista,
        'paises_disponibles': paises_disponibles,
        'mostrar_tester_asignado': mostrar_tester_asignado,
        'mostrar_paises': mostrar_paises,
        'feature_files': list(matriz.feature_files.all().order_by('nombre_archivo')),
    })


@login_required
def actualizar_estado_caso(request):
    if request.method == "POST":
        caso_id = request.POST.get("caso_id")
        nuevo_estado = request.POST.get("nuevo_estado")
        try:
            caso = CasoDePrueba.objects.get(id=caso_id)
            caso.estado = nuevo_estado
            caso.save()

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"matriz_{caso.matriz.id}",
                {
                    "type": "estado_actualizado",
                    "data": {
                        "caso_id": caso.id,
                        "valor": nuevo_estado,
                        "tipo": "estado",
                    },
                }
            )
            return JsonResponse({"success": True})
        except CasoDePrueba.DoesNotExist:
            return JsonResponse({"success": False, "error": "Caso no encontrado."})
    return JsonResponse({"success": False, "error": "Método no permitido."})

@require_POST
@login_required
def actualizar_nota_caso(request):
    caso_id = request.POST.get('caso_id')
    nueva_nota = request.POST.get('nota', '')

    try:
        caso = CasoDePrueba.objects.get(id=caso_id)
        caso.nota = nueva_nota
        caso.save()

        # Emitir a WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"matriz_{caso.matriz.id}",
            {
                "type": "nota_actualizada",
                "data": {
                    "caso_id": caso.id,
                    "valor": nueva_nota,
                }
            }
        )
        return JsonResponse({"success": True})
    except CasoDePrueba.DoesNotExist:
        return JsonResponse({"success": False, "error": "No encontrado"}, status=404)
@login_required
def editar_validates(request, super_matriz_id):
    super_matriz = get_object_or_404(SuperMatriz, id=super_matriz_id)

    #Validates ordenados por ticket ascendente (para la tabla)
    validates = Validate.objects.filter(
        super_matriz=super_matriz
    ).order_by('ticket')

    detalles_validate = getattr(super_matriz, 'detalles_validate', None)

    #Testers únicos sin repetir (para los botones de filtro)
    testers = (
        Validate.objects
        .filter(super_matriz=super_matriz)
        .values_list('tester', flat=True)
        .distinct()
    )

    # Construcción de formularios
    formularios = []
    if request.method == 'POST':
        for validate in validates:
            form = ValidateEstadoForm(
                request.POST,
                prefix=str(validate.id),
                instance=validate
            )
            if form.is_valid():
                form.save()
        return redirect('matrix_app:editar_validates', super_matriz_id=super_matriz.id)
    else:
        for validate in validates:
            form = ValidateEstadoForm(
                prefix=str(validate.id),
                instance=validate
            )
            formularios.append((validate, form))

    return render(request, 'excel_files/editar_validates.html', {
        'super_matriz': super_matriz,
        'formularios_validates': formularios,
        'detalles_validate': detalles_validate,
        'testers': testers,
    })
@login_required
@require_POST
@csrf_exempt
def actualizar_estado_validate(request):
    try:
        validate_id = request.POST.get('validate_id')
        nuevo_estado = request.POST.get('nuevo_estado')
        
        # Validar parámetros
        if not validate_id or not nuevo_estado:
            return JsonResponse({'error': 'Parámetros faltantes'}, status=400)
        
        # Obtener y actualizar el validate
        validate = Validate.objects.get(id=validate_id)
        validate.estado = nuevo_estado
        validate.save()
        
        return JsonResponse({'success': True})
        
    except Validate.DoesNotExist:
        return JsonResponse({'error': 'Validate no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
@login_required
def detalles_validate_modal(request, super_matriz_id):
    super_matriz = get_object_or_404(SuperMatriz, id=super_matriz_id)
    detalles, _ = DetallesValidate.objects.get_or_create(super_matriz=super_matriz)
    testers_del_equipo = User.objects.filter(equipo_nuevo=super_matriz.equipo_nuevo)
    if request.method == 'POST':
        form = DetallesValidateForm(request.POST, instance=detalles)
        form.fields['testers'].queryset = testers_del_equipo

        if form.is_valid():
            detalles = form.save(commit=False)
            detalles.super_matriz = super_matriz
            detalles.save()

            testers_seleccionados = form.cleaned_data['testers']

            if not Validate.objects.filter(super_matriz=super_matriz).exists():
                if detalles.filtro_RN:  
                    importar_validates(super_matriz, detalles.filtro_RN, testers_seleccionados)

            return redirect('matrix_app:detalle_super_matriz', super_matriz_id=super_matriz.id)
    else:
        form = DetallesValidateForm(instance=detalles)
        form.fields['testers'].queryset = testers_del_equipo

    return render(request, 'excel_files/detalles_validate_modal.html', {
        'form': form,
        'super_matriz': super_matriz,
    })
def tickets_por_levantar_view(request, super_matriz_id):
    
    super_matriz = get_object_or_404(SuperMatriz, id=super_matriz_id)
    tickets = TicketPorLevantar.objects.filter(super_matriz=super_matriz)

    if request.method == 'POST':
        form = TicketPorLevantarForm(request.POST)
        if form.is_valid():
            nuevo_ticket = form.save(commit=False)
            nuevo_ticket.super_matriz = super_matriz
            nuevo_ticket.tester_asignado = request.user
            nuevo_ticket.save()
            return redirect('matrix_app:tickets_por_levantar', super_matriz_id=super_matriz.id)
        else:
            
            messages.error(request, f"Error al crear ticket: {form.errors}")
    else:
       
        form = TicketPorLevantarForm()

    return render(request, 'excel_files/tickets_por_levantar.html', {
        'super_matriz': super_matriz,
        'tickets': tickets,
        'form': form,
    })

@login_required
def editar_ticket(request, ticket_id):
    ticket = get_object_or_404(TicketPorLevantar, id=ticket_id)

    if request.method == 'POST':
        ticket.ticket_SCT = request.POST.get('ticket_SCT', '').strip()
        ticket.BRF = request.POST.get('BRF', '').strip()
        ticket.desc = request.POST.get('desc', '').strip()
        ticket.prioridad = request.POST.get('prioridad', '')  # Nueva línea
        ticket.nota = request.POST.get('nota', '').strip()
        ticket.url = request.POST.get('url', '').strip()
        ticket.save()
        
        return redirect('matrix_app:tickets_por_levantar', super_matriz_id=ticket.super_matriz.id)

@login_required
def eliminar_super_matriz(request, super_matriz_id):
    matriz = get_object_or_404(SuperMatriz, id=super_matriz_id)
    if request.method == "POST":
        matriz.delete()
        messages.success(request, "Matriz eliminada correctamente.")
        return redirect('home') 
    return render(request, 'home.html', {'matriz': matriz})


@login_required
@require_POST
def eliminar_matriz(request, matriz_id):
    matriz = get_object_or_404(Matriz, id=matriz_id)
    super_matriz_id = matriz.super_matriz.id
    matriz.delete()
    return redirect('matrix_app:detalle_super_matriz', super_matriz_id=super_matriz_id)


def generar_pdf_supermatriz(request, supermatriz_id):
    super_matriz = get_object_or_404(SuperMatriz, id=supermatriz_id)
    matrices = super_matriz.matrices.all()
    
    matrices_info = []
    paises_globales = set()
    total_global_casos = 0
    total_global_completados = 0

    for matriz in matrices:
        # Usar la función optimizada
        matriz_info = obtener_informacion_matriz(matriz.id)
        
        if matriz_info:
            total_global_casos += matriz_info['total_casos']
            total_global_completados += matriz_info['casos_ejecutados']
            
            # Agregar países al conjunto global
            for pais in matriz_info['paises']:
                paises_globales.add(pais)
            
            # Determinar el tipo de alcance
            alcance = {
                'A': "MVP (Minimum Viable Product:A)",
                'A,B': 'Smoke Test (A,B)',
                'A,B,C': 'No Afectación (NA:A,B,C)'
            }.get(matriz_info['alcance'], 'No definido')
            
            # Obtener número de fallos
            num_fallos = matriz_fails(matriz)[0]['indice']
            #print(f"{matriz_info['num_externos']} {matriz_info['externos']}")
            matrices_info.append({
                'matriz': matriz,
                'total_casos': matriz_info['total_casos'],
                'casos_filtrados': matriz_info['casos_ejecutados'],
                'porcentaje': matriz_info['porcentaje'],
                'paises': matriz_info['paises'],  # Países específicos de esta matriz
                'alcance': alcance,
                'num_fallos': num_fallos,
                'dispositivo': matriz_info['dispositivo'],
                'testers': matriz_info['testers'],
                'num_externos':matriz_info['num_externos'],
                'externos':matriz_info['externos']
            })

    porcentaje_total = round((total_global_completados / total_global_casos * 100), 2) if total_global_casos > 0 else 0
    fecha_generacion = localtime().strftime('%d de %B de %Y')

    # Renderizar HTML
    template = get_template('pdf/reporte_supermatriz.html')
    html_string = template.render({
        'super_matriz': super_matriz,
        'matrices_info': matrices_info,
        'paises_globales': sorted(paises_globales),  # Todos los países de todas las matrices
        'porcentaje_total': porcentaje_total,
        'fecha_generacion': fecha_generacion,
        'total_global_casos': total_global_casos,
        'total_global_completados': total_global_completados,
    })

    # Generar el PDF con WeasyPrint
    html = HTML(string=html_string)
    result = html.write_pdf()

    # Devolver el PDF como respuesta
    response = HttpResponse(result, content_type='application/pdf')
    
    # Forzar la descarga con el nombre del archivo
    filename = f"reporte_{super_matriz.nombre.replace(' ', '_')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # Agregar headers adicionales para forzar descarga
    response['Content-Transfer-Encoding'] = 'binary'
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    return response    
User = get_user_model()

@login_required
def asignar_validates(request, super_matriz_id):
    super_matriz = get_object_or_404(SuperMatriz, id=super_matriz_id)
    validates = Validate.objects.filter(super_matriz=super_matriz)

    # Usamos equipo_nuevo, que es un FK a Equipo
    testers = User.objects.filter(cargo='Tester', equipo_nuevo=super_matriz.equipo_nuevo)

    if request.method == "POST":
        for validate in validates:
            nuevo_tester = request.POST.get(f"tester_{validate.id}")
            if nuevo_tester:
                validate.tester = nuevo_tester  # Se guarda como string
                validate.save()
        return redirect('matrix_app:editar_validates', super_matriz_id=super_matriz.id)
        

    context = {
        'super_matriz': super_matriz,
        'validates': validates,
        'testers': testers,
    }
    return render(request, 'excel_files/asignar_validates.html', context)

@login_required
def dashboard(request):
    colores = ["#093FB4", "#dc3545", "#198754", "#E67514", "#6f42c1", "#4B352A", "#2F5249"]

    # Obtener todos los equipos
    equipos = Equipo.objects.all().order_by("id")

    # Obtener todas las supermatrices NO ARCHIVADAS con sus matrices
    supermatrices = SuperMatriz.objects.filter(archivado=False).select_related("equipo_nuevo").prefetch_related("matrices").all()

    # Diccionario temporal para agrupar la información
    equipos_dict = {}
    for idx, eq in enumerate(equipos):
        equipos_dict[eq.id] = {
            "id": eq.id,
            "nombre": eq.nombre,
            "color": colores[idx % len(colores)],
            "supermatrices": []
        }

    # Agrupar supermatrices por equipo
    for sm in supermatrices:
        # LLAMAR A LA FUNCIÓN EXTERNA
        info_matrices = matriz_info(sm.matrices.all())

        if sm.equipo_nuevo_id in equipos_dict:
            matrices_list = []

            for m in sm.matrices.all():
                # Buscar la info correspondiente a esta matriz
                m_info = next((info for info in info_matrices if info["matriz"].id == m.id), None)
                
                # Obtener información de fallas para esta matriz
                fallas_info = matriz_fails(m)
                if fallas_info:
                    fallas_data = fallas_info[0]  # Tomar el primer elemento del array
                else:
                    fallas_data = {'indice': 0, 'casos_filtrados': []}

                matrices_list.append({
                    "id": m.id,
                    "nombre": m.nombre,
                    "info": {
                        "total_casos": m_info["total_casos"] if m_info else 0,
                        "casos_filtrados": m_info["casos_filtrados"] if m_info else 0,
                        "porcentaje": m_info["porcentaje"] if m_info else 0,
                        "testers_por_region": m_info["testers_por_region"] if m_info else {},
                        "alcance": m_info["alcance"] if m_info else "",
                        "dispositivo": m_info["dispositivo"] if m_info else "",
                        "fallas": fallas_data  # Nueva información de fallas
                    }
                })

            equipos_dict[sm.equipo_nuevo_id]["supermatrices"].append({
                "id": sm.id,
                "nombre": sm.nombre,
                "fecha_creacion": sm.fecha_creacion.strftime('%Y-%m-%d'),
                "fecha_fin": sm.fecha_fin.strftime('%Y-%m-%d') if sm.fecha_fin else None,
                "matrices": matrices_list
            })

    # Convertir a lista para enviar al template
    equipos_data = list(equipos_dict.values())

    # Preparar datos para el calendario
    matrices_data = []
    for eq in equipos_data:
        for sm in eq["supermatrices"]:
            matrices_data.append({
                "equipo": eq["nombre"],
                "supermatriz": sm["nombre"],
                "fecha_creacion": sm["fecha_creacion"],
                "fecha_fin": sm["fecha_fin"],
                "color": eq["color"],
                "matrices": [
                    {
                        "id": m["id"],
                        "nombre": m["nombre"],
                        "info": m["info"]
                    } for m in sm["matrices"]
                ]
            })

    context = {
        "matrices_json": json.dumps(matrices_data, default=str),
        "equipos_json": json.dumps(equipos_data, default=str),
    }
    
    return render(request, 'excel_files/dashboard.html', context)


@login_required
def subir_feature(request, super_matriz_id=None, matriz_id=None):
    """
    Subir un archivo .feature: crea nueva matriz o añade a una existente (matriz_id por URL o GET/POST).
    """
    super_matrices = SuperMatriz.objects.all().order_by('nombre')
    dispositivos = Dispositivo.objects.all().order_by('nombre')
    matriz_existente = None
    matriz_id = matriz_id or request.GET.get('matriz_id') or request.POST.get('matriz_id')
    if matriz_id:
        try:
            matriz_existente = Matriz.objects.get(id=int(matriz_id))
        except (ValueError, Matriz.DoesNotExist):
            matriz_existente = None

    initial = {}
    if super_matriz_id:
        initial['super_matriz'] = get_object_or_404(SuperMatriz, id=super_matriz_id)
    elif matriz_existente:
        initial['super_matriz'] = matriz_existente.super_matriz

    if request.method == 'POST':
        form = FeatureUploadForm(request.POST, request.FILES)
        archivos = request.FILES.getlist('feature_files') or (
            [request.FILES['feature_file']] if request.FILES.get('feature_file') else []
        )
        errores = []
        for a in archivos:
            if a.name.lower().endswith('.feature') and a.size <= 2 * 1024 * 1024:
                continue
            if not a.name.lower().endswith('.feature'):
                errores.append(f"'{a.name}' no tiene extensión .feature")
            elif a.size > 2 * 1024 * 1024:
                errores.append(f"'{a.name}' supera los 2 MB")
        if archivos and errores:
            for e in errores:
                messages.error(request, e)
        elif archivos and (form.is_valid() or matriz_existente):
            super_matriz = form.cleaned_data.get('super_matriz') or (matriz_existente and matriz_existente.super_matriz)
            dispositivo = form.cleaned_data.get('dispositivo') if form.is_valid() else (matriz_existente and matriz_existente.dispositivo)
            if not super_matriz:
                messages.error(request, "Falta seleccionar Super Matriz.")
            else:
                matriz_id_redirect = None
                if matriz_existente:
                    for archivo in archivos:
                        if not archivo.name.lower().endswith('.feature') or archivo.size > 2 * 1024 * 1024:
                            continue
                        try:
                            ff = FeatureFile(
                                super_matriz=matriz_existente.super_matriz,
                                dispositivo=matriz_existente.dispositivo,
                                matriz=matriz_existente,
                            )
                            ff.archivo_feature.save(archivo.name, archivo, save=True)
                            sync_scenarios_from_featurefile(ff)
                            matriz_id_redirect = matriz_existente.id
                        except Exception as e:
                            messages.error(request, f"Error al subir '{archivo.name}': {e}")
                    if matriz_id_redirect:
                        messages.success(request, f"{len(archivos)} archivo(s) .feature añadidos a la matriz.")
                        return redirect('matrix_app:detalle_matriz', matriz_id=matriz_id_redirect)
                else:
                    # Varios archivos = una sola matriz (regla de negocio)
                    nombre_matriz = archivos[0].name[:70] if archivos else "Matriz Gherkin"
                    matriz = Matriz.objects.create(
                        super_matriz=super_matriz,
                        nombre=nombre_matriz,
                        alcances_utilizados='A',
                        dispositivo=dispositivo,
                    )
                    for archivo in archivos:
                        if not archivo.name.lower().endswith('.feature') or archivo.size > 2 * 1024 * 1024:
                            continue
                        try:
                            ff = FeatureFile(
                                super_matriz=super_matriz,
                                dispositivo=dispositivo,
                                matriz=matriz,
                            )
                            ff.archivo_feature.save(archivo.name, archivo, save=True)
                            sync_scenarios_from_featurefile(ff)
                        except Exception as e:
                            messages.error(request, f"Error al subir '{archivo.name}': {e}")
                    messages.success(request, f"{len(archivos)} archivo(s) .feature subidos en una matriz. Escenarios sincronizados.")
                    return redirect('matrix_app:detalle_matriz', matriz_id=matriz.id)
    else:
        form = FeatureUploadForm(initial=initial)

    super_matriz_id_default = super_matriz_id if super_matriz_id else (matriz_existente.super_matriz_id if matriz_existente else (super_matrices.first().id if super_matrices else None))

    return render(request, 'excel_files/subir_feature.html', {
        'form': form,
        'super_matrices': super_matrices,
        'dispositivos': dispositivos,
        'super_matriz_id_default': super_matriz_id_default,
        'matriz_existente': matriz_existente,
    })


@login_required
def subir_otro_feature(request, matriz_id):
    """Añadir otro archivo .feature a una matriz existente."""
    return subir_feature(request, super_matriz_id=None, matriz_id=matriz_id)


@login_required
def vista_previa_gherkin(request, feature_file_id):
    """
    Vista previa de un archivo .feature (por id). Muestra el contenido en una página.
    """
    feature_file = get_object_or_404(FeatureFile, id=feature_file_id)
    matriz = feature_file.matriz
    if not matriz:
        messages.error(request, "Este archivo .feature no está asociado a una matriz.")
        return redirect('matrix_app:detalle_super_matriz', super_matriz_id=feature_file.super_matriz_id)

    path = feature_file.get_feature_path()
    if not path or not os.path.exists(path):
        messages.error(request, "El archivo .feature no existe en el servidor.")
        return redirect('matrix_app:detalle_matriz', matriz_id=matriz.id)

    try:
        with open(path, 'r', encoding='utf-8') as f:
            contenido = f.read()
    except Exception as e:
        messages.error(request, f"No se pudo leer el archivo: {e}")
        return redirect('matrix_app:detalle_matriz', matriz_id=matriz.id)

    return render(request, 'excel_files/vista_previa_gherkin.html', {
        'matriz': matriz,
        'feature_file': feature_file,
        'contenido': contenido,
        'nombre_archivo': feature_file.nombre_archivo,
    })


@login_required
def vista_previa_gherkin_todos(request, matriz_id):
    """
    Vista previa de todos los archivos .feature de una matriz en una sola página (acordeón).
    """
    matriz = get_object_or_404(Matriz, id=matriz_id)
    feature_files = list(matriz.feature_files.all().order_by('nombre_archivo'))
    if not feature_files:
        messages.error(request, "Esta matriz no tiene archivos .feature asociados.")
        return redirect('matrix_app:detalle_matriz', matriz_id=matriz_id)

    archivos_con_contenido = []
    for ff in feature_files:
        path = ff.get_feature_path()
        contenido = ""
        if path and os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    contenido = f.read()
            except Exception:
                contenido = "(No se pudo leer el archivo)"
        else:
            contenido = "(Archivo no encontrado en el servidor)"
        archivos_con_contenido.append({'feature_file': ff, 'contenido': contenido})

    return render(request, 'excel_files/vista_previa_gherkin_todos.html', {
        'matriz': matriz,
        'archivos_con_contenido': archivos_con_contenido,
    })


def _feature_file_path_safe(feature_file):
    """Comprueba que la ruta del .feature esté dentro de FEATURES_ROOT. Devuelve (path, error)."""
    path = feature_file.get_feature_path()
    if not path:
        return None, "Archivo sin ruta"
    features_root = os.path.realpath(getattr(settings, 'FEATURES_ROOT', ''))
    if not features_root:
        return None, "Configuración inválida"
    path_real = os.path.realpath(path)
    if not path_real.startswith(features_root):
        return None, "Ruta no permitida"
    return path_real, None


@login_required
def editor_feature(request, feature_file_id):
    """
    Carga la página del editor del archivo .feature (Monaco + guardado HTTP).
    Sin edición colaborativa en tiempo real; simplifica dependencias.
    """
    feature_file = get_object_or_404(FeatureFile, id=feature_file_id)
    path, err = _feature_file_path_safe(feature_file)
    if err or not path or not os.path.exists(path):
        messages.error(request, err or "El archivo no existe en el servidor.")
        if feature_file.matriz_id:
            return redirect('matrix_app:detalle_matriz', matriz_id=feature_file.matriz_id)
        return redirect('matrix_app:detalle_super_matriz', super_matriz_id=feature_file.super_matriz_id)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            contenido = f.read()
    except Exception as e:
        messages.error(request, f"No se pudo leer el archivo: {e}")
        if feature_file.matriz_id:
            return redirect('matrix_app:detalle_matriz', matriz_id=feature_file.matriz_id)
        return redirect('matrix_app:detalle_super_matriz', super_matriz_id=feature_file.super_matriz_id)

    return render(request, 'excel_files/editor_feature.html', {
        'feature_file': feature_file,
        'matriz': feature_file.matriz,
        'contenido': contenido,
        'nombre_archivo': feature_file.nombre_archivo,
        'feature_file_id': feature_file_id,
    })


@login_required
@require_POST
def guardar_feature_file(request, feature_file_id):
    """
    Guarda el contenido del archivo .feature en disco, actualiza SHA256 y sincroniza escenarios.
    Acepta POST con body JSON { "content": "..." } o form-data content=...
    """
    feature_file = get_object_or_404(FeatureFile, id=feature_file_id)
    path, err = _feature_file_path_safe(feature_file)
    if err or not path:
        return JsonResponse({'success': False, 'error': err or 'Ruta no permitida'}, status=400)

    content = None
    content_type = request.content_type or ''
    if 'application/json' in content_type:
        try:
            data = json.loads(request.body)
            content = data.get('content')
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    else:
        content = request.POST.get('content')

    if content is None:
        return JsonResponse({'success': False, 'error': 'Falta el contenido'}, status=400)

    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

    # Recalcula SHA256, actualiza BD y re-sincroniza escenarios (conserva estados)
    sync_scenarios_from_featurefile(feature_file)

    return JsonResponse({
        'success': True,
        'message': 'Archivo guardado correctamente. Los escenarios se han sincronizado; los nuevos Scenario o Scenario Outline aparecen como casos de prueba en la matriz.',
    })


@login_required
def vincular_csv_feature(request, feature_file_id):
    """
    Vincular un CSV a un .feature para expandir Scenario Outline (una fila = un caso de prueba).
    GET: formulario de subida. POST: guarda el CSV y re-sincroniza.
    """
    feature_file = get_object_or_404(FeatureFile, id=feature_file_id)
    if request.method == 'POST':
        archivo = request.FILES.get('archivo_csv')
        if not archivo:
            messages.error(request, "Seleccione un archivo CSV.")
            return redirect('matrix_app:vincular_csv_feature', feature_file_id=feature_file_id)
        if not archivo.name.lower().endswith('.csv'):
            messages.error(request, "Solo se permiten archivos .csv")
            return redirect('matrix_app:vincular_csv_feature', feature_file_id=feature_file_id)
        if archivo.size > 5 * 1024 * 1024:
            messages.error(request, "El CSV no puede superar 5 MB.")
            return redirect('matrix_app:vincular_csv_feature', feature_file_id=feature_file_id)
        feature_file.archivo_csv.save(archivo.name, archivo, save=True)
        sync_scenarios_from_featurefile(feature_file)
        messages.success(request, "CSV vinculado. Los Scenario Outline se han expandido en casos de prueba (una fila = un caso).")
        if feature_file.matriz_id:
            return redirect('matrix_app:detalle_matriz', matriz_id=feature_file.matriz_id)
        return redirect('matrix_app:gestionar_features')
    return render(request, 'excel_files/vincular_csv_feature.html', {
        'feature_file': feature_file,
    })


@login_required
@require_POST
def quitar_csv_feature(request, feature_file_id):
    """Quita el CSV vinculado y re-sincroniza (los Scenario Outline vuelven a ser un caso cada uno)."""
    feature_file = get_object_or_404(FeatureFile, id=feature_file_id)
    if feature_file.archivo_csv:
        feature_file.archivo_csv.delete(save=False)
        feature_file.archivo_csv = None
        feature_file.save(update_fields=['archivo_csv'])
    sync_scenarios_from_featurefile(feature_file)
    messages.success(request, "CSV desvinculado. Escenarios actualizados.")
    if feature_file.matriz_id:
        return redirect('matrix_app:detalle_matriz', matriz_id=feature_file.matriz_id)
    return redirect('matrix_app:gestionar_features')


@login_required
def gestionar_features(request):
    """
    Lista los archivos .feature subidos con opciones para ver, editar y eliminar.
    Filtro opcional: ?super_matriz_id=X
    """
    super_matriz_id = request.GET.get('super_matriz_id')
    queryset = FeatureFile.objects.select_related('super_matriz', 'matriz', 'dispositivo').order_by('-creado_en')
    if super_matriz_id:
        queryset = queryset.filter(super_matriz_id=super_matriz_id)
    feature_files = list(queryset)
    super_matrices = SuperMatriz.objects.all().order_by('nombre')
    return render(request, 'excel_files/gestionar_features.html', {
        'feature_files': feature_files,
        'super_matrices': super_matrices,
        'super_matriz_id_filtro': int(super_matriz_id) if super_matriz_id else None,
    })


@login_required
@require_POST
def eliminar_feature_file(request, feature_file_id):
    """
    Elimina un archivo .feature: borra el archivo físico, el FeatureFile,
    FeatureScenario (CASCADE) y los CasoDePrueba asociados (por scenario_stable_id).
    """
    feature_file = get_object_or_404(FeatureFile, id=feature_file_id)
    super_matriz_id = feature_file.super_matriz_id
    matriz_id = feature_file.matriz_id
    path, err = _feature_file_path_safe(feature_file)
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass
    if feature_file.archivo_csv:
        feature_file.archivo_csv.delete(save=False)
    prefix = f"{feature_file.id}-"
    CasoDePrueba.objects.filter(matriz_id=matriz_id, scenario_stable_id__startswith=prefix).delete()
    feature_file.delete()
    messages.success(request, f"Archivo '{feature_file.nombre_archivo}' eliminado correctamente.")
    if matriz_id:
        return redirect('matrix_app:detalle_matriz', matriz_id=matriz_id)
    return redirect('matrix_app:detalle_super_matriz', super_matriz_id=super_matriz_id)


@login_required
def editar_fecha_fin(request, pk):
    supermatriz = get_object_or_404(SuperMatriz, pk=pk)

    if request.method == "POST":
        form = SuperMatrizFechaFinForm(request.POST, instance=supermatriz)
        if form.is_valid():
            form.save()
            messages.success(request, "Fecha fin actualizada correctamente.")
            return redirect('home')
        else:
            messages.error(request, "Error al actualizar la fecha.")
    
    return redirect('home')@login_required
def obtener_num_fallos(request, matriz_id):
    matriz = get_object_or_404(Matriz, id=matriz_id)
    data = matriz_fails(matriz)
    num_fallos = data[0]['indice']
    return JsonResponse({"num_fallos": num_fallos})
def archivar_super_matriz(request, matriz_id):
    if request.method == 'POST':
        matriz = get_object_or_404(SuperMatriz, id=matriz_id)
        matriz.archivar()
        messages.success(request, f'La matriz "{matriz.nombre}" ha sido archivada correctamente.')
    return redirect('home')
@login_required
def matrices_archivadas(request):
    """Vista para ver y gestionar matrices archivadas"""
    # Solo líderes y superusuarios pueden ver las matrices archivadas
    if not (request.user.is_superuser or request.user.cargo == "Lider"):
        messages.error(request, "No tienes permisos para ver las matrices archivadas.")
        return redirect('home')
    
    equipo = request.GET.get('equipo')
    equipo_nuevo = request.GET.get('equipo_nuevo')
    ver_todos = request.GET.get('ver_todos')

    # Filtrado de matrices archivadas
    matrices_archivadas_list = SuperMatriz.objects.filter(archivado=True)

    # Aplicar filtros de equipo
    if equipo_nuevo:
        matrices_archivadas_list = matrices_archivadas_list.filter(equipo_nuevo=equipo_nuevo)
    elif equipo:
        matrices_archivadas_list = matrices_archivadas_list.filter(equipo=equipo)

    # Ordenar por fecha de creación (más recientes primero)
    matrices_archivadas_list = matrices_archivadas_list.order_by('-fecha_creacion')
    
    # Paginación
    paginator = Paginator(matrices_archivadas_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    equipos = Equipo.objects.all()
    
    return render(request, "excel_files/matrices_archivadas.html", {
        'page_obj': page_obj,
        'matrices_count': matrices_archivadas_list.count(),
        'equipos': equipos,
        'equipo_filtrado': equipo_nuevo or equipo,
    })

@login_required
def desarchivar_super_matriz(request, matriz_id):
    """Vista para desarchivar una matriz"""
    if request.method == 'POST':
        matriz = get_object_or_404(SuperMatriz, id=matriz_id)
        matriz.archivado = False
        matriz.save()
        messages.success(request, f'La matriz "{matriz.nombre}" ha sido desarchivada correctamente.')
    return redirect('matrix_app:matrices_archivadas')
def editar_descripcion(request, pk):
    supermatriz = get_object_or_404(SuperMatriz, pk=pk)

    if request.method == "POST":
        form = SuperMatrizDescripcionForm(request.POST, instance=supermatriz)
        if form.is_valid():
            form.save()
            messages.success(request, "Descripción actualizada correctamente.")
            return redirect('home')
    else:
        form = SuperMatrizDescripcionForm(instance=supermatriz)

    context = {
        "form": form,
        "supermatriz": supermatriz
    }
    return render(request, "home.html", context)
def descargar_pdf_equipo(request, equipo_id):
    """
    View para descargar un PDF con todas las supermatrices de un equipo
    """
    try:
        # Obtener información completa del equipo usando nuestras funciones
        resultado_equipo = obtener_supermatrices_por_equipo_con_filtros(
            equipo_id, 
            solo_activas=True
        )
        
        if not resultado_equipo:
            return HttpResponse("Equipo no encontrado", status=404)
        
        # Obtener información detallada de cada supermatriz y sus matrices
        equipo_info_detallado = {
            'equipo_nombre': resultado_equipo['equipo_nombre'],
            'supermatrices': []
        }
        
        for supermatriz in resultado_equipo['supermatrices']:
            # Obtener matrices de esta supermatriz
            matrices_info = obtener_matrices_por_supermatriz(supermatriz['id'])
            
            supermatriz_detallada = {
                'id': supermatriz['id'],
                'nombre': supermatriz['nombre'],
                'descripcion': supermatriz['descripcion'],
                'fecha_creacion': supermatriz['fecha_creacion'],
                'fecha_fin': supermatriz['fecha_fin'],
                'matrices_info': matrices_info['matrices'] if matrices_info else []
            }
            
            equipo_info_detallado['supermatrices'].append(supermatriz_detallada)
        
        # Crear el contenido HTML para el PDF
        html_string = render_to_string('pdf/reporte_equipo.html', {
            'equipo': equipo_info_detallado,
            'fecha_generacion': timezone.now().strftime("%d/%m/%Y"),
        })
        
        # Crear PDF
        html = HTML(string=html_string, base_url=request.build_absolute_uri())
        
        # Crear respuesta HTTP con el PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="reporte_equipo_{resultado_equipo["equipo_nombre"]}.pdf"'
        
        # Generar PDF
        html.write_pdf(response)
        
        return response
        
    except Exception as e:
        print(f"Error generando PDF: {e}")
        return HttpResponse("Error generando el PDF", status=500)
def descargar_pdf_todos_equipos(request):
    """
    View para descargar un PDF con TODOS los equipos y sus supermatrices completas
    """
    try:
        # Usar nuestra función para obtener todos los equipos completos
        resultado_completo = obtener_todos_los_equipos_completo(solo_activas=True)
        
        if not resultado_completo or not resultado_completo['equipos']:
            return HttpResponse("No hay datos para generar el PDF", status=404)
        
        # Filtrar equipos excluyendo "Gerencia" y "Visitors"
        equipos_filtrados = [
            equipo for equipo in resultado_completo['equipos'] 
            if equipo['nombre'] not in ['Gerencia', 'Visitors']
        ]
        
        # Crear el contenido HTML para el PDF
        html_string = render_to_string('pdf/reporte_todos_equipos.html', {
            'equipos': equipos_filtrados,
            'fecha_generacion': timezone.now().strftime("%d/%m/%Y"),
            'total_equipos': len(equipos_filtrados),
            'total_supermatrices': sum(len(equipo['supermatrices']) for equipo in equipos_filtrados)
        })
        
        # Crear PDF
        html = HTML(string=html_string, base_url=request.build_absolute_uri())
        
        # Crear respuesta HTTP con el PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="reporte_completo_equipos.pdf"'
        
        # Generar PDF
        html.write_pdf(response)
        
        return response
        
    except Exception as e:
        print(f"Error generando PDF completo: {e}")
        return HttpResponse("Error generando el PDF completo", status=500)
@login_required
def obtener_num_fallos(request, matriz_id):
    matriz = get_object_or_404(Matriz, id=matriz_id)
    data = matriz_fails(matriz)
    num_fallos = data[0]['indice']
    return JsonResponse({"num_fallos": num_fallos})



@csrf_exempt
def verify_session(request):
    """Endpoint para que Nginx verifique si el usuario está autenticado"""
    if request.user.is_authenticated:
        return HttpResponse(status=200)  # Usuario logueado
    return HttpResponse(status=401)  # No autorizado
