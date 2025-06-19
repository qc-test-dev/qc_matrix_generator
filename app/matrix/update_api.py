# app/matrix/update_api.py

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from app.matrix.models import CasoDePrueba

@csrf_exempt
def api_guardar_estado(request):
    if request.method == 'POST':
        try:
            body_unicode = request.body.decode('utf-8')
            data = json.loads(body_unicode)
            registros = data.get('registros', [])

            if not registros:
                return JsonResponse({'status': 'error', 'error': 'No se recibieron registros'}, status=400)

            for r in registros:
                CasoDePrueba.objects.filter(id=r["id"]).update(
                    estado=r["estado"],
                    nota=r["nota"]
                )

            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'error': str(e)}, status=400)

    return JsonResponse({'error': 'Método no permitido'}, status=405)
