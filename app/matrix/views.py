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
    TicketPorLevantarForm,ValidateForm,SuperMatrizFechaFinForm,SuperMatrizDescripcionForm
)
from .models import SuperMatriz, Matriz, Validate,TicketPorLevantar,DetallesValidate,Dispositivo,Equipo
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
locale.setlocale(locale.LC_TIME, 'es_MX.UTF-8')
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import SuperMatriz, Matriz
from .forms import MatrizForm, ValidateForm
from django.utils import timezone
import os
import random
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
        casos_externos= matriz_obj.casos.all().filter(estado__in=['pendiente_por_externo']).count()
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
            'externos':casos_externos
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

                ruta_excel_matriz = os.path.join(settings.BASE_DIR, 'static', 'excel_files', dispositivo.matriz_base)
                if not os.path.exists(ruta_excel_matriz):
                    messages.error(request, f"El archivo '{dispositivo.matriz_base}' no existe en el servidor.")
                    return redirect('matrix_app:detalle_super_matriz', super_matriz_id=super_matriz.id)

                importar_matriz_desde_excel(nueva_matriz, ruta_excel_matriz, valores_a_incluir)

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
    num_fallos = matriz_fails(matriz)[0]['indice']
    
    # Casos de prueba base
    casos_de_prueba = matriz.casos.all()

    # Aplicar filtro por tester (viejo) si existe
    if tester_filtrado:
        casos_de_prueba = casos_de_prueba.filter(tester=tester_filtrado)
    
    # CORRECCIÓN: Filtrar por ID del tester_asignado
    if tester_asignado_filtrado and pais_filtrado:
        # Filtrar por ID del tester Y país
        try:
            tester_id = int(tester_asignado_filtrado)
            casos_de_prueba = casos_de_prueba.filter(
                tester_asignado__id=tester_id,
                pais=pais_filtrado
            )
        except (ValueError, TypeError):
            # Si no es un ID válido, intentar filtrar por nombre
            casos_de_prueba = casos_de_prueba.filter(
                tester_asignado__nombre__icontains=tester_asignado_filtrado.split()[0],
                pais=pais_filtrado
            )
    elif tester_asignado_filtrado:
        # Solo filtrar por ID del tester
        try:
            tester_id = int(tester_asignado_filtrado)
            casos_de_prueba = casos_de_prueba.filter(
                tester_asignado__id=tester_id
            )
        except (ValueError, TypeError):
            # Si no es un ID válido, intentar filtrar por nombre
            casos_de_prueba = casos_de_prueba.filter(
                tester_asignado__nombre__icontains=tester_asignado_filtrado.split()[0]
            )
    elif pais_filtrado:
        # Solo filtrar por país
        casos_de_prueba = casos_de_prueba.filter(pais=pais_filtrado)

    # Ordenar los casos
    casos_de_prueba = casos_de_prueba.order_by("fase", "id")

    # Aplicar filtro de fallo usando la función matriz_fails
    if fallo_filtrado == 'bloqueante':
        fallos = matriz_fails(matriz)
        casos_filtrados = fallos[0]['casos_filtrados']
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
    testers_disponibles = list(matriz.casos.exclude(tester='').exclude(tester__isnull=True).values_list('tester', flat=True).distinct())
    
    # NUEVO: Obtener los IDs de los testers asignados para filtrado preciso
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
            'tester_nombre': nombre_completo,  # Cambiado a nombre completo
            'pais': pais
        })
    
    # Determinar qué botones mostrar
    mostrar_botones_viejos = len(testers_disponibles) > 0
    mostrar_botones_nuevos = len(botones_nuevos) > 0  # Cambiado: mostrar ambos si existen

    # determinar si hay datos en la matriz (etiqueta,tipo_usuario,pasos
    campos = {
    "etiqueta": casos_de_prueba.filter(etiqueta__isnull=False).exclude(etiqueta="").exists(),
    "tipo_usuario": casos_de_prueba.filter(tipo_usuario__isnull=False).exclude(tipo_usuario="").exists(),
    "pasos": casos_de_prueba.filter(pasos__isnull=False).exclude(pasos="").exists(),
    "mdp": casos_de_prueba.filter(mdp__isnull=False).exclude(mdp="").exists(),
    "monto": casos_de_prueba.filter(monto__isnull=False).exclude(monto="").exists(),
    "navegador": casos_de_prueba.filter(navegador__isnull=False).exclude(navegador="").exists(),
    }

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
        'fallos': fallos if fallo_filtrado == 'bloqueante' else [],
        'num_fallos': num_fallos,
        'mostrar_botones_viejos': mostrar_botones_viejos,
        'mostrar_botones_nuevos': mostrar_botones_nuevos,
        'campos': campos,
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
