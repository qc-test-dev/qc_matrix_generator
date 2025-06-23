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
    TicketPorLevantarForm,ValidateForm
)
from .models import SuperMatriz, Matriz, Validate,TicketPorLevantar,DetallesValidate
from .utils import importar_matriz_desde_excel,importar_validates
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
from .utils import importar_matriz_desde_excel  # Asegúrate de tener esta función
from django.views.decorators.csrf import csrf_exempt
@login_required
def detalle_super_matriz(request, super_matriz_id):
    super_matriz = get_object_or_404(SuperMatriz, id=super_matriz_id)
    matrices = super_matriz.matrices.all()
    validates = super_matriz.validates.all()
    es_lider = request.user.cargo == 'Lider'

    # Mapeo de equipos a archivos Excel
    RUTA_EXCEL_EQUIPOS = {
        'Claro TV STB - IPTV - Roku - TATA': 'static/excel_files/matriz_base.xlsx',
        'STV (LG,Samsung,ADR), Kepler-FireTV, STV2(Hisense,Netrange)': 'static/excel_files/matriz_base.xlsx',
        'WIN - WEB - Fire TV': 'static/excel_files/matriz_base.xlsx',
        'IOS - TvOS': 'static/excel_files/matriz_base.xlsx',
        'Android': 'static/excel_files/matriz_base.xlsx',
        'Smart TV AAF': 'static/excel_files/matriz_base.xlsx',
    }

    matrices_info = []
    for matriz in matrices:
        casos = matriz.casos.all()
        total_casos = casos.count()
        estados_interes = ['funciona', 'falla_nueva', 'falla_persistente',"na"]
        casos_filtrados = casos.filter(estado__in=estados_interes).count()
        porcentaje = (casos_filtrados / total_casos * 100) if total_casos > 0 else 0

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
        })

    form = MatrizForm(equipo=super_matriz.equipo)
    validate_form = ValidateForm()

    if request.method == 'POST':
        if 'crear_matriz' in request.POST:
            form = MatrizForm(request.POST, equipo=super_matriz.equipo)
            if form.is_valid():
                nueva_matriz = form.save(commit=False)
                nueva_matriz.super_matriz = super_matriz

                alcance_seleccionado = request.POST.get('alcance', '')
                valores_a_incluir = set(alcance_seleccionado.split(',')) if alcance_seleccionado else set()

                nueva_matriz.alcances_utilizados = ",".join(sorted(valores_a_incluir))
                nueva_matriz.save()

                # Obtener la ruta del Excel correspondiente al equipo
                ruta_excel_matriz = RUTA_EXCEL_EQUIPOS.get(super_matriz.equipo)

                if not ruta_excel_matriz:
                    messages.error(request, f"No hay archivo Excel configurado para el equipo: {super_matriz.equipo}")
                    return redirect('matrix_app:detalle_super_matriz', super_matriz_id=super_matriz.id)

                ruta_absoluta = os.path.join(settings.BASE_DIR, ruta_excel_matriz)
                if not os.path.exists(ruta_absoluta):
                    messages.error(request, f"El archivo '{ruta_excel_matriz}' no existe en el servidor.")
                    return redirect('matrix_app:detalle_super_matriz', super_matriz_id=super_matriz.id)

                importar_matriz_desde_excel(nueva_matriz, ruta_excel_matriz, valores_a_incluir)

                testers_seleccionados = list(form.cleaned_data.get('testers', []))
                regiones_seleccionados = form.cleaned_data.get('regiones', [])
                casos = list(nueva_matriz.casos.all())
                random.shuffle(regiones_seleccionados)
                random.shuffle(testers_seleccionados)
                random.shuffle(casos)
                for idx, caso in enumerate(casos):
                    tester = testers_seleccionados[idx % len(testers_seleccionados)] if testers_seleccionados else ''
                    region = regiones_seleccionados[idx % len(regiones_seleccionados)] if regiones_seleccionados else ''
                    caso.tester = f"{tester.nombre}-{region}" if tester and region else ''
                    caso.save()

                return redirect('matrix_app:detalle_super_matriz', super_matriz_id=super_matriz.id)

        elif 'crear_validate' in request.POST:
            validate_form = ValidateForm(request.POST)
            if validate_form.is_valid():
                validate = validate_form.save(commit=False)
                validate.super_matriz = super_matriz
                validate.save()
                return redirect('matrix_app:detalle_super_matriz', super_matriz_id=super_matriz.id)

    return render(request, 'excel_files/detalle_super_matriz.html', {
        'super_matriz': super_matriz,
        'matrices_info': matrices_info,
        'form': form,
        'validate_form': validate_form,
        'validates': validates,
        'es_lider': es_lider,
    })

# @login_required
# def detalle_super_matriz(request, super_matriz_id):
#     super_matriz = get_object_or_404(SuperMatriz, id=super_matriz_id)
#     matrices = super_matriz.matrices.all()
#     validates = super_matriz.validates.all()
#     es_lider = request.user.cargo=='Lider'
    
#     matrices_info = []
#     for matriz in matrices:
#         casos = matriz.casos.all()
#         total_casos = casos.count()
#         estados_interes = ['funciona', 'falla_nueva', 'falla_persistente']
#         casos_filtrados = casos.filter(estado__in=estados_interes).count()
#         porcentaje = (casos_filtrados / total_casos * 100) if total_casos > 0 else 0

#         testers_por_region = defaultdict(set)
#         for caso in casos:
#             if caso.tester:
#                 partes = caso.tester.split('-')
#                 if len(partes) == 2:
#                     nombre, region = partes
#                     testers_por_region[region.strip()].add(nombre.strip())

#         # Convertir sets a listas ordenadas
#         testers_por_region = {region: sorted(list(nombres)) for region, nombres in testers_por_region.items()}

#         matrices_info.append({
#             'matriz': matriz,
#             'total_casos': total_casos,
#             'casos_filtrados': casos_filtrados,
#             'porcentaje': round(porcentaje, 2),
#             'testers_por_region': testers_por_region,
#         })
#     # Formulario vacío al principio
#     form = MatrizForm(equipo=super_matriz.equipo)
#     validate_form = ValidateForm()

#     if request.method == 'POST':
#         if 'crear_matriz' in request.POST:
#             form = MatrizForm(request.POST, equipo=super_matriz.equipo)
#             if form.is_valid():
#                 nueva_matriz = form.save(commit=False)
#                 nueva_matriz.super_matriz = super_matriz

#                 alcance_seleccionado = request.POST.get('alcance', '')
#                 valores_a_incluir = set(alcance_seleccionado.split(',')) if alcance_seleccionado else set()

#                 nueva_matriz.alcances_utilizados = ",".join(sorted(valores_a_incluir))
#                 nueva_matriz.save()

#                 ruta_excel_matriz = os.path.join('static', 'excel_files', 'matriz_base.xlsx')
#                 importar_matriz_desde_excel(nueva_matriz, ruta_excel_matriz, valores_a_incluir)

#                 testers_seleccionados = list(form.cleaned_data.get('testers', []))
#                 regiones_seleccionados = form.cleaned_data.get('regiones', [])
#                 casos = list(nueva_matriz.casos.all())
#                 random.shuffle(regiones_seleccionados)
#                 random.shuffle(testers_seleccionados)
#                 random.shuffle(casos)
#                 for idx, caso in enumerate(casos):
#                     tester = testers_seleccionados[idx % len(testers_seleccionados)] if testers_seleccionados else ''
#                     region = regiones_seleccionados[idx % len(regiones_seleccionados)] if regiones_seleccionados else ''
#                     caso.tester = f"{tester.nombre}-{region}" if tester and region else ''
#                     caso.save()

#                 return redirect('matrix_app:detalle_super_matriz', super_matriz_id=super_matriz.id)

#         elif 'crear_validate' in request.POST:
#             validate_form = ValidateForm(request.POST)
#             if validate_form.is_valid():
#                 validate = validate_form.save(commit=False)
#                 validate.super_matriz = super_matriz
#                 validate.save()
#                 return redirect('matrix_app:detalle_super_matriz', super_matriz_id=super_matriz.id)

#     return render(request, 'excel_files/detalle_super_matriz.html', {
#         'super_matriz': super_matriz,
#         'matrices_info': matrices_info,
#         'form': form,
#         'validate_form': validate_form,
#         'validates': validates,
#         'es_lider': es_lider,
#     })
@login_required
def detalle_matriz(request, matriz_id):
    matriz = get_object_or_404(Matriz, id=matriz_id)
    super_matriz_id = matriz.super_matriz.id

    testers_disponibles = matriz.casos.values_list('tester', flat=True).distinct()
    casos_de_prueba = matriz.casos.all()
    tester_filtrado = request.GET.get('tester')
    if tester_filtrado:
        casos_de_prueba = casos_de_prueba.filter(tester=tester_filtrado)

    casos_de_prueba = casos_de_prueba.order_by("fase", "id")

    alcances_lista = []
    if matriz.alcances_utilizados:
        alcances_lista = matriz.alcances_utilizados.split(',')

    formularios_casos_de_prueba = [
        (caso, CasoDePruebaForm(instance=caso, prefix=f"caso_{caso.id}"))
        for caso in casos_de_prueba
    ]

    return render(request, 'excel_files/detalle_matriz.html', {
        'matriz': matriz,
        'super_matriz_id': super_matriz_id,
        'alcances_lista': alcances_lista,
        'formularios_casos_de_prueba': formularios_casos_de_prueba,
        'testers_disponibles': testers_disponibles,
        'tester_filtrado': tester_filtrado,
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

@csrf_exempt
@login_required
def actualizar_nota_caso(request):
    if request.method == "POST":
        caso_id = request.POST.get("caso_id")
        nueva_nota = request.POST.get("nota")
        try:
            caso = CasoDePrueba.objects.get(id=caso_id)
            caso.nota = nueva_nota
            caso.save()

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"matriz_{caso.matriz.id}",
                {
                    "type": "nota_actualizada",
                    "data": {
                        "caso_id": caso.id,
                        "valor": nueva_nota,
                        "tipo": "nota",
                    },
                }
            )
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
    return JsonResponse({"success": False, "error": "Método no permitido."})
@login_required
def editar_validates(request, super_matriz_id):
    super_matriz = get_object_or_404(SuperMatriz, id=super_matriz_id)

    # 1️⃣ Validates ordenados por ticket ascendente (para la tabla)
    validates = Validate.objects.filter(
        super_matriz=super_matriz
    ).order_by('ticket')

    detalles_validate = getattr(super_matriz, 'detalles_validate', None)

    # 2️⃣ Testers únicos sin repetir (para los botones de filtro)
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
def detalles_validate_modal(request, super_matriz_id):
    super_matriz = get_object_or_404(SuperMatriz, id=super_matriz_id)
    detalles, _ = DetallesValidate.objects.get_or_create(super_matriz=super_matriz)
    testers_del_equipo = User.objects.filter(equipo=super_matriz.equipo)
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
@login_required
def actualizar_estado_validate(request):
    if request.method == 'POST':
        validate_id = request.POST.get('validate_id')
        nuevo_estado = request.POST.get('nuevo_estado')

        try:
            validate = Validate.objects.get(id=validate_id)
            validate.estado = nuevo_estado
            validate.save()

            # WebSocket: enviar actualización a todos los clientes del grupo
            super_matriz = validate.super_matriz  # Asumiendo que tienes esta relación
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"validates_{super_matriz.id}",
                {
                    "type": "estado_actualizado",
                    "validate_id": validate.id,
                    "nuevo_estado": nuevo_estado,
                }
            )

            return JsonResponse({"success": True})
        except Validate.DoesNotExist:
            return JsonResponse({"success": False, "error": "Validate no encontrado"})
    return JsonResponse({"success": False, "error": "Método no permitido"})
def tickets_por_levantar_view(request, super_matriz_id):
    super_matriz = get_object_or_404(SuperMatriz, id=super_matriz_id)
    tickets = TicketPorLevantar.objects.filter(super_matriz=super_matriz)

    if request.method == 'POST':
        form = TicketPorLevantarForm(request.POST, super_matriz=super_matriz)
        if form.is_valid():
            nuevo_ticket = form.save(commit=False)
            nuevo_ticket.super_matriz = super_matriz
            nuevo_ticket.save()
            return redirect('matrix_app:tickets_por_levantar', super_matriz_id=super_matriz.id)
    else:
        form = TicketPorLevantarForm(super_matriz=super_matriz)

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
        ticket.nota = request.POST.get('nota', '').strip()
        ticket.url = request.POST.get('url', '').strip()
        ticket.save()
        
        # Redirige a la página de lista de tickets de la supermatriz
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
