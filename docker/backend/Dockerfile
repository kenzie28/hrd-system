# NOTE: build context must be the repo root, e.g.:
#   docker build -f docker/backend/Dockerfile -t hrd-backend .
# (see docker/docker-compose.yml, which does this automatically)

FROM python:3.12-slim

WORKDIR /app/backend

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

COPY docker/backend/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
