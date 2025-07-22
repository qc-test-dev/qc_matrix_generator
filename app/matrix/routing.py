from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Para matrices (IDs numéricos)
    re_path(r'^ws/matriz/(?P<matriz_id>\d+)/$', consumers.MatrizConsumer.as_asgi()),
    
    # Para validaciones (IDs numéricos o UUIDs)
    re_path(r'^ws/validates/(?P<super_matriz_id>[\w-]+)/$', consumers.ValidatesConsumer.as_asgi()),
    
    # Endpoint de prueba/diagnóstico
    re_path(r'^ws/test/$', consumers.TestConsumer.as_asgi()),
]