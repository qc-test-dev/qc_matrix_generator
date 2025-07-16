from .base import *

CSRF_TRUSTED_ORIGINS = [
    'http://200.57.172.7',
    'http://200.57.172.7:80',
    'http://200.57.172.7:8080',
    'http://0.0.0.0',
    'http://0.0.0.0:80',
    'http://localhost',
    'http://localhost:80',
]
DEBUG = True

SESSION_COOKIE_NAME = 'uat_sessionid'
CSRF_COOKIE_NAME = 'uat_csrftoken'
ALLOWED_HOSTS = [
    '200.57.172.7',
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
]
