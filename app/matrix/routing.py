# routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/matriz/(?P<matriz_id>\w+)/$", consumers.MatrizConsumer.as_asgi()),
    re_path(r"ws/validate/(?P<super_matriz_id>\w+)/$", consumers.ValidateConsumer.as_asgi()),
]
    