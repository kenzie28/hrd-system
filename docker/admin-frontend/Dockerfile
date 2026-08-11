# NOTE: build context must be the repo root, e.g.:
#   docker build -f docker/admin-frontend/Dockerfile -t hrd-admin-frontend .
# (see docker/docker-compose.yml, which does this automatically)

FROM node:22-alpine AS build
WORKDIR /app
COPY admin-frontend/package.json admin-frontend/package-lock.json ./
RUN npm ci
COPY admin-frontend/ ./

# Always bake relative /api — browser hits the same host:port as the SPA.
ENV VITE_API_URL=/api
ENV VITE_API_KEY=

RUN npm run build \
 && grep -R -q '/api' dist/assets \
 || (echo "ERROR: built SPA does not reference /api — check admin-frontend api client." >&2; exit 1)

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
# Stock nginx entrypoint runs envsubst on *.template → conf.d/default.conf
# only substitutes ${ENV_VAR} (e.g. ${API_KEY}); nginx $uri stays intact.
COPY docker/admin-frontend/nginx.conf.template /etc/nginx/templates/default.conf.template
RUN rm -f /etc/nginx/conf.d/default.conf

EXPOSE 80
# Keep the image default ENTRYPOINT [/docker-entrypoint.sh] + CMD nginx.
