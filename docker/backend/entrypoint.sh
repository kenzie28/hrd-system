#!/bin/bash
set -e

cd /app/backend

echo "==> Waiting for MySQL at ${DB_HOST:-mysql}:${DB_PORT:-3306}..."
python <<'PY'
import os
import sys
import time

import pymysql

host = os.environ.get("DB_HOST", "mysql")
port = int(os.environ.get("DB_PORT", "3306"))
user = os.environ.get("DB_USER", "admin")
password = os.environ.get("DB_PASSWORD", "")
name = os.environ.get("DB_NAME", "hrd_system")

for attempt in range(60):
    try:
        conn = pymysql.connect(host=host, port=port, user=user, password=password, database=name)
        conn.close()
        print("MySQL is ready.")
        break
    except Exception as exc:
        print(f"MySQL not ready yet ({exc}); retrying ({attempt + 1}/60)...")
        time.sleep(2)
else:
    sys.exit("MySQL did not become ready in time.")
PY

echo "==> Running migrations..."
python manage.py migrate --noinput

# Idempotent: ensures HQ lokasi + admin karyawan 0000003 (Kenzie Mihardja) exist.
# Password defaults to 123 and is only set when the portal user is first created.
echo "==> Ensuring default admin karyawan (0000003 / Kenzie Mihardja)..."
python manage.py shell < /app/backend/scripts/initial_setup.py

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

if [ -n "${DJANGO_SUPERUSER_USERNAME}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD}" ]; then
    echo "==> Ensuring Django superuser '${DJANGO_SUPERUSER_USERNAME}' exists with the configured password..."
    DJANGO_SUPERUSER_USERNAME="${DJANGO_SUPERUSER_USERNAME}" \
    DJANGO_SUPERUSER_PASSWORD="${DJANGO_SUPERUSER_PASSWORD}" \
    DJANGO_SUPERUSER_EMAIL="${DJANGO_SUPERUSER_EMAIL:-admin@example.com}" \
    python manage.py shell <<'PY'
import os

from django.contrib.auth import get_user_model

User = get_user_model()
username = os.environ["DJANGO_SUPERUSER_USERNAME"]
password = os.environ["DJANGO_SUPERUSER_PASSWORD"]
email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@example.com")

user, created = User.objects.get_or_create(
    username=username,
    defaults={"email": email, "is_staff": True, "is_superuser": True},
)
user.is_staff = True
user.is_superuser = True
user.email = email
user.set_password(password)
user.save()
print(("Created" if created else "Updated") + f" superuser '{username}'.")
PY
fi

echo "==> Starting gunicorn on 0.0.0.0:8000..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
