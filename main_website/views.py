# Django views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from app.matrix.models import SuperMatriz
from app.matrix.forms import SuperMatrizForm
from django.core.paginator import Paginator



@login_required
def home(request):
    # Obtener todas las super matrices
    super_matrices_list = SuperMatriz.objects.all().order_by('-fecha_creacion')  # Ordenar por fecha descendente
    
    # Paginar (5 elementos por página)
    paginator = Paginator(super_matrices_list, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.method == 'POST':
        form = SuperMatrizForm(request.POST)
        if form.is_valid():
            super_matriz = form.save()
            return redirect('matrix_app:detalles_validate_modal', super_matriz_id=super_matriz.id)
    else:
        form = SuperMatrizForm()

    return render(request, "home.html", {
        'form': form,
        'page_obj': page_obj, 
    })
def login_redirect(request):
    if not request.user.is_authenticated:
        return redirect("/accounts/login/")
    return redirect("/home/")

