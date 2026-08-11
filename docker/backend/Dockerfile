# NOTE: build context must be the repo root, e.g.:
#   docker build -f docker/backend/Dockerfile -t hrd-backend .
# (see docker/docker-compose.yml, which does this automatically)

FROM python:3.12-slim

WORKDIR /app/backend

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Fail the image build if app migrations were not included (common when
# migrations were gitignored or the build machine only has __init__.py).
RUN test -f core/migrations/0001_initial.py \
 && test -f karyawan/migrations/0001_initial.py \
 && test -f absensi/migrations/0001_initial.py \
 && test -f shift/migrations/0001_initial.py \
 && test -f cuti/migrations/0001_initial.py \
 && test -f gaji/migrations/0001_initial.py \
 && test -f lembur/migrations/0001_initial.py \
 && test -f liburan/migrations/0001_initial.py \
 || (echo "ERROR: Django migration files missing from image. Commit backend/*/migrations/*.py and rebuild." >&2; exit 1)

COPY docker/backend/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
