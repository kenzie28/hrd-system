#!/bin/bash
set -e

cd /app/backend

echo "==> Running migrations..."
python manage.py migrate --noinput

if [ "${RUN_INITIAL_SETUP}" = "true" ]; then
    echo "==> Running initial setup (lokasi + admin karyawan)..."
    python manage.py shell < /app/backend/scripts/initial_setup.py
fi

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

if [ -n "${DJANGO_SUPERUSER_USERNAME}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD}" ]; then
    echo "==> Ensuring Django superuser exists..."
    python manage.py createsuperuser --noinput \
        --username "${DJANGO_SUPERUSER_USERNAME}" \
        --email "${DJANGO_SUPERUSER_EMAIL:-admin@example.com}" \
        2>/dev/null || true
fi

echo "==> Starting gunicorn..."
GUNICORN_LOG_LEVEL="${GUNICORN_LOG_LEVEL:-info}"
gunicorn config.wsgi:application \
    --bind 127.0.0.1:8000 \
    --workers 2 \
    --timeout 120 \
    --log-level "${GUNICORN_LOG_LEVEL}" \
    --access-logfile - \
    --error-logfile - &

echo "==> Starting nginx on port 8080..."
exec nginx -g 'daemon off;'
