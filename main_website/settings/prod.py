from .base import *

CSRF_TRUSTED_ORIGINS = [
    'http://200.57.172.7',
    'http://200.57.172.7:80',
    'http://200.57.172.7:8080',
]
allowed_hosts = ['200.57.172.7', 'localhost', '127.0.0.1','0.0.0.0','*']

DEBUG = False

SESSION_COOKIE_NAME = 'prod_sessionid'
CSRF_COOKIE_NAME = 'prod_csrftoken'
