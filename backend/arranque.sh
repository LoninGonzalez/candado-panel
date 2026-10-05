#!/bin/sh
set -e
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py crear_admin
# Render inyecta el puerto en $PORT; local usa 8000
gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3
