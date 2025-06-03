#!/bin/sh
set -e
python3 manage.py collectstatic --noinput
python3 manage.py migrate
python3 manage.py compilemessages
python3 manage.py makemigrations
uwsgi --socket :8000 --master --enable-threads --module app.wsgi