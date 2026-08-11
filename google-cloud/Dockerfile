# NOTE: build context must be the repo root, e.g.:
#   docker build -f google-cloud/Dockerfile -t hrd-system .
# (see google-cloud/deploy.sh, which does this automatically)

# --- Admin frontend build ---
FROM node:22-alpine AS admin-build
WORKDIR /app/admin-frontend
COPY admin-frontend/package.json admin-frontend/package-lock.json ./
RUN npm ci
COPY admin-frontend/ ./
ENV VITE_API_URL=/api
ENV VITE_BASE_PATH=/hr/
RUN npm run build

# --- Portal frontend build ---
FROM node:22-alpine AS portal-build
WORKDIR /app/portal-frontend
COPY portal-frontend/package.json portal-frontend/package-lock.json ./
RUN npm ci
COPY portal-frontend/ ./
ENV VITE_API_URL=/api
ENV VITE_BASE_PATH=/portal/
RUN npm run build

# --- Final image ---
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Fail if app migrations missing (e.g. gitignored migrations in build context).
RUN test -f core/migrations/0001_initial.py \
 && test -f karyawan/migrations/0001_initial.py \
 || (echo "ERROR: Django migration files missing from image. Commit backend/*/migrations/*.py." >&2; exit 1)

COPY google-cloud/nginx.conf /etc/nginx/conf.d/default.conf
COPY google-cloud/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

COPY --from=admin-build /app/admin-frontend/dist /var/www/hr
COPY --from=portal-build /app/portal-frontend/dist /var/www/portal

EXPOSE 8080

ENTRYPOINT ["/docker-entrypoint.sh"]
