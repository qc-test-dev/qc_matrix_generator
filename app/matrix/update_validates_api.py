import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from app.matrix.models import Validate

@csrf_exempt
def api_guardar_validates(request):
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)
    try:
        data = json.loads(request.body)
        regs = data.get("registros", [])
        if not regs:
            return JsonResponse({"status": "error", "error": "Sin registros"}, status=400)
        for r in regs:
            Validate.objects.filter(id=r["id"]).update(estado=r["estado"])
        return JsonResponse({"status": "ok"})
    except Exception as e:
        return JsonResponse({"status": "error", "error": str(e)}, status=400)
