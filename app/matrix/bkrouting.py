# tu_app/routing.py
from django.urls import re_path
from app.matrix import bkconsumers



websocket_urlpatterns = [
    re_path(r'^ws/matriz/(?P<matriz_id>\d+)/$', bkconsumers.MatrizConsumer.as_asgi()),
    re_path(r'^ws/validates/(?P<super_matriz_id>\d+)/$', bkconsumers.ValidateConsumer.as_asgi()),
]