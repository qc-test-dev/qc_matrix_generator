

CORRER EN AMBIENTE VIRTUAL SOLAMENTE(llamarlo venv, por convención del proyecto)
dentro del ambiente virtual instalar librerias pip
pip install -r requirements.txt

** necesario migrar BBDD 

python manage.py migrate
python manage.py loaddata datos.json
python manage.py runserver 8080 (o puede ser en 8081)


2- ws-scrcpy  ejecutar servidor con npm start (npm install -g ws-scrcpy, para instalar)
** antes de iniciar la apk web de Django para poder ver los streams de los dispos es necesarioejecutar ws-scrcpy


****************

pendientes
1- refactorizar el codigo
2- requiremtnst.txt----- HECHO
LUIS 3- agregar control rcu  CUANDO SE ABRA VENTANA DE STREAM QUE SEA MAS grande Y TENGA rcu a lado
3- el stream de rtmp, en vez de ws-scrcpy  ( aún no iniciar)
LUIS 4- el stream mas grande


LUIS
Panel de dispostivos cambiar en el titulo, en vez de que diga STB que diga dispositivos.
dispositivos conectados....e nla pantalla media, quitar STB

Alberto/Luis
1-ftp de versiones. crear apk ftp para guardar versiones
2-API para subir versiones a FTP o Script SSH..
3- REFACTOR codigo Y QUITAR TEMPLATE ANTIGUOS


Luis
2- luis crear nueva apk web en este proyecto para manuales de instalacion FW, APK, para todas las marcas de STB y TV

# Implementacion de websockets en el proyecto 23/06/2025
## 1.- Instalar Django Channels
pip install channels
## 2.- Agregar a INSTALLED_APPS en settings.py:
INSTALLED_APPS = [
    # ...
    'channels',
]

## 3.- Configurar ASGI en settings.py
ASGI_APPLICATION = 'main_website.wsgi.asgi.application'

## 4.- Modificar archivo asgi.py (Crear si es necesario)
import os
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
import main_website.routing  # Aquí estará el archivo de las+3 rutas WebSocket

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main_website.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            main_website.routing.websocket_urlpatterns
        )
    ),
})
## 5.- Crear archivo routing.py en la app a usar
## 6.- Crear archivo 
## 7.- Configurar Redis como backend del channel_layer 
### es un servicio necesario para que ws funcione 
### paara docker
docker run -p 6379:6379 -d redis
### para sistema en general sin uso de docker
sudo apt update
sudo apt install redis
### Instala soporte Redis en env
pip install channels_redis
### Configurar en settings.py
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}
# Explicacion de cada uso 
¿Qué significa cada parte?
🔹 "default"
Es el nombre de la capa de canal por defecto. Puedes tener más de una si lo necesitas, pero normalmente con "default" basta.

🔹 "BACKEND": "channels_redis.core.RedisChannelLayer"
Indica que vamos a usar Redis como backend para gestionar los canales.
Este backend es el que permite la comunicación entre procesos o usuarios conectados. Está implementado por el paquete channels_redis

🔹 "CONFIG": {"hosts": [("127.0.0.1", 6379)]}
Esta es la configuración específica para Redis:

"127.0.0.1" → la dirección IP local de tu máquina (localhost).

6379 → el puerto por defecto de Redis.

En conjunto, esto significa:

"Conéctate al servidor Redis que está corriendo en mi computadora local en el puerto 6379."

##  Agregar cliente WebSocket en HTML ya depende de cada vista 

## IMPORTANTE instalaremos Daphne (ya no se usara python manage.py runserver para correr el proyecto)
## Nueva Forma de correr el proyecto 
daphne -e tcp:port=8081:interface=127.0.0.1 main_website.asgi:application

## Para que funcione esto se cambio 
# instalar whitenoise
pip install whitenoise
# Modificar en bk_settings.py
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    # ... resto de middlewares
]
## en bk_settings.py se modifico 

STATIC_URL = '/static/'

## Esta carpeta será donde Django recopilará todos los archivos estáticos cuando corras collectstatic
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Opcional: para mejor cacheo y compresión
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
# Se ejecuto 
python manage_local.py collectstatic
# Para ejecutar en servidor 
daphne -e tcp:port=8081:interface=127.0.0.1 main_website.asgi:application


# Agregar todos los usuarios de los equipos 24/06/2025
se modifico en accounts y matrix 
forms.py 
EQUIPO_CHOICES=(
    ('Claro TV STB - IPTV - Roku - TATA','Claro TV STB - IPTV - Roku - TATA'),
    ('STV (LG,Samsung,ADR), Kepler-FireTV, STV2(Hisense,Netrange)','STV (LG,Samsung,ADR), Kepler-FireTV, STV2(Hisense,Netrange)'),
    ('IPTV AOSP','IPTV AOSP'),
    ('WIN - WEB - Fire TV','WIN - WEB - Fire TV'),
    ('IOS - TvOS','IOS - TvOS'),
    ('Android','Android'),
    ('Smart TV AAF','Smart TV AAF')
)
y en models.py se modifico en accounts y matrix
EQUIPO_CHOICES=(
    ('Claro TV STB - IPTV - Roku - TATA','Claro TV STB - IPTV - Roku - TATA'),
    ('STV (LG,Samsung,ADR), Kepler-FireTV, STV2(Hisense,Netrange)','STV (LG,Samsung,ADR), Kepler-FireTV, STV2(Hisense,Netrange)'),
    ('IPTV AOSP','IPTV AOSP'),
    ('WIN - WEB - Fire TV','WIN - WEB - Fire TV'),
    ('IOS - TvOS','IOS - TvOS'),
    ('Android','Android'),
    ('Smart TV AAF','Smart TV AAF')
)
Se aplico un 
python manage_local.py makemigrations
python manage_local.py migrate

### Se arreglo el ws 
# desde aqui hare los cambios de los modelos 



#Creacion y modificacion de equipos y generacion de nuevas matrices 
pasos a relalizar 
python manage_local.py makemigrations
python manage_local.py migrate
