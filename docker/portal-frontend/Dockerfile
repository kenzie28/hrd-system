# NOTE: build context must be the repo root, e.g.:
#   docker build -f docker/portal-frontend/Dockerfile -t hrd-portal-frontend .
# (see docker/docker-compose.yml, which does this automatically)

FROM node:22-alpine AS build
WORKDIR /app
COPY portal-frontend/package.json portal-frontend/package-lock.json ./
RUN npm ci
COPY portal-frontend/ ./

ENV VITE_API_URL=/api
ENV VITE_API_KEY=

RUN npm run build \
 && grep -R -q '/api' dist/assets \
 || (echo "ERROR: built SPA does not reference /api — check portal-frontend api client." >&2; exit 1)

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY docker/portal-frontend/nginx.conf.template /etc/nginx/templates/default.conf.template
RUN rm -f /etc/nginx/conf.d/default.conf

EXPOSE 80
