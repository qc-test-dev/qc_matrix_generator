from .base import *

CSRF_TRUSTED_ORIGINS = [
    'http://localhost',
    'http://localhost:80',
    'http://localhost:8080',
]

DEBUG = True

SESSION_COOKIE_NAME = 'uat_sessionid'
CSRF_COOKIE_NAME = 'uat_csrftoken'
ALLOWED_HOSTS = ['localhost', '127.0.0.1','0.0.0.0','*','200.57.172.7']