#!/bin/sh
set -e
# Sincronización de esquema de un solo uso. Déjala mientras el modelo aún cambia en
# desarrollo; es idempotente (no toca nada si el esquema ya coincide) y conserva datos.
# Para producción estable, puedes quitarla y usar solo 'migrate'.
python manage.py reparar_migraciones || true
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py crear_admin
gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3
