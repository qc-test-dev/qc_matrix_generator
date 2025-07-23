# tu_app/routing.py
from django.urls import re_path
from app.matrix import consumers

websocket_urlpatterns = [
    re_path(r'ws/matriz/(?P<matriz_id>\d+)/$', consumers.MatrizConsumer.as_asgi()),
    re_path(r'ws/validates/(?P<super_matriz_id>\d+)/$', consumers.ValidateConsumer.as_asgi()),
]