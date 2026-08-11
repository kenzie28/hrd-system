# NOTE: build context must be the repo root, e.g.:
#   docker build -f docker/portal-frontend/Dockerfile -t hrd-portal-frontend .
# (see docker/docker-compose.yml, which does this automatically)

FROM node:22-alpine AS build
WORKDIR /app
COPY portal-frontend/package.json portal-frontend/package-lock.json ./
RUN npm ci
COPY portal-frontend/ ./

# Same-origin /api (proxied by nginx at runtime). Absolute overrides via build arg
# only needed for unusual multi-host setups.
ARG VITE_API_URL=/api
ARG VITE_API_KEY=
ENV VITE_API_URL=${VITE_API_URL}
ENV VITE_API_KEY=${VITE_API_KEY}

RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
# envsubst on container start: injects API_KEY into the proxy header.
COPY docker/portal-frontend/nginx.conf.template /etc/nginx/templates/default.conf.template

EXPOSE 80
