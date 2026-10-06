#!/bin/sh
set -e
python manage.py reparar_migraciones || true
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py crear_admin
gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3
