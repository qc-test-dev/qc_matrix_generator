# Django views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from app.matrix.models import SuperMatriz
from app.matrix.forms import SuperMatrizForm
from django.core.paginator import Paginator
from app.accounts.forms import UserCreateForm

@login_required
def home(request):
    equipo = request.GET.get('equipo')
    if equipo:
        super_matrices_list = SuperMatriz.objects.filter(equipo=equipo).order_by('-fecha_creacion')
    else:
        super_matrices_list = SuperMatriz.objects.all().order_by('-fecha_creacion')

    paginator = Paginator(super_matrices_list, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    es_lider = request.user.cargo == "Lider"

    matriz_form = SuperMatrizForm() if es_lider else None
    usuario_form = UserCreateForm() if request.user.is_superuser else None

    if request.method == 'POST' and es_lider and 'nombre' in request.POST and 'descripcion' in request.POST:
        matriz_form = SuperMatrizForm(request.POST)
        if matriz_form.is_valid():
            super_matriz = matriz_form.save()
            return redirect('matrix_app:detalles_validate_modal', super_matriz_id=super_matriz.id)

    equipos = ['Roku', 'STV(TATA)', 'STB', 'WEB', 'IOS']

    return render(request, "home.html", {
        'matriz_form': matriz_form,
        'usuario_form': usuario_form,
        'page_obj': page_obj,
        'equipos': equipos,
        'equipo_filtrado': equipo,
        'es_lider': es_lider,
    })