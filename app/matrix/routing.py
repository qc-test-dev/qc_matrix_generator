# app/matrix/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/matriz/(?P<matriz_id>\d+)/$', consumers.MatrizConsumer.as_asgi()),
    re_path(r'ws/validates/(?P<super_matriz_id>\d+)/$', consumers.ValidatesConsumer.as_asgi()),
]