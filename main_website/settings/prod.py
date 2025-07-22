from .base import *

CSRF_TRUSTED_ORIGINS = [
    'http://200.57.172.7',
    'http://localhost',
    'http://127.0.0.1',
]


ALLOWED_HOSTS = [
    '200.57.172.7',
    'localhost',
    '127.0.0.1',
]



DEBUG = False

SESSION_COOKIE_NAME = 'prod_sessionid'
CSRF_COOKIE_NAME = 'prod_csrftoken'
