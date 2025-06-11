# Django views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from app.matrix.models import SuperMatriz
from app.matrix.forms import SuperMatrizForm
from django.core.paginator import Paginator
from app.accounts.forms import UserCreateForm

@login_required
def home(request):
    super_matrices_list = SuperMatriz.objects.all().order_by('-fecha_creacion')  
    paginator = Paginator(super_matrices_list, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    matriz_form = SuperMatrizForm()
    usuario_form = UserCreateForm()

    # Solo procesamos el formulario de matriz aquí (por nombre)
    if request.method == 'POST' and 'nombre' in request.POST and 'descripcion' in request.POST:
        matriz_form = SuperMatrizForm(request.POST)
        if matriz_form.is_valid():
            super_matriz = matriz_form.save()
            return redirect('matrix_app:detalles_validate_modal', super_matriz_id=super_matriz.id)

    return render(request, "home.html", {
        'matriz_form': matriz_form,
        'usuario_form': usuario_form,
        'page_obj': page_obj, 
    })
