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
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

COPY --from=admin-build /app/admin-frontend/dist /var/www/hr
COPY --from=portal-build /app/portal-frontend/dist /var/www/portal

EXPOSE 8080

ENTRYPOINT ["/docker-entrypoint.sh"]
