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

DEBUG = True

SESSION_COOKIE_NAME = 'uat_sessionid'
CSRF_COOKIE_NAME = 'uat_csrftoken'
