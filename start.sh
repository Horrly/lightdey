#!/usr/bin/env bash
# Render start: migrate, add starter areas (names only), then serve.
set -o errexit
cd backend

python manage.py migrate --noinput
python manage.py seed_areas

exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers 2 --timeout 60 --access-logfile -
