#!/bin/bash
# =============================================================================
# Build the Docker images for the whole HRD System ecosystem:
#   mysql, backend, admin-frontend, portal-frontend
# =============================================================================
# Usage: ./build.sh
#
# On first run this creates docker/.env (from .env.example) and generates
# random values for API_KEY and DJANGO_SECRET_KEY if they are left blank.
# The API key is required on every request to the backend (`X-Api-Key`
# header) and is baked into both frontend bundles at build time, so it must
# exist *before* `docker compose build` runs.
#
# After building, start the stack with:
#   docker compose up -d
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

ENV_FILE="${SCRIPT_DIR}/.env"
ENV_EXAMPLE="${SCRIPT_DIR}/.env.example"

if [ ! -f "${ENV_FILE}" ]; then
    echo "==> Creating docker/.env from .env.example..."
    cp "${ENV_EXAMPLE}" "${ENV_FILE}"
fi

random_hex() {
    if command -v openssl &>/dev/null; then
        openssl rand -hex 32
    else
        head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n'
    fi
}

# Sets KEY to VALUE in .env, but only if KEY is currently missing or blank.
# Leaves any existing non-blank value untouched.
ensure_env_var() {
    local key="$1"
    local generated_value="$2"
    local current
    current="$(grep -E "^${key}=" "${ENV_FILE}" | head -n1 | cut -d'=' -f2-)"

    if [ -n "${current}" ]; then
        return
    fi

    if grep -qE "^${key}=" "${ENV_FILE}"; then
        sed -i.bak "s|^${key}=.*|${key}=${generated_value}|" "${ENV_FILE}" && rm -f "${ENV_FILE}.bak"
    else
        echo "${key}=${generated_value}" >> "${ENV_FILE}"
    fi
    echo "==> Generated a random value for ${key} in docker/.env"
}

ensure_env_var "API_KEY" "$(random_hex)"
ensure_env_var "DJANGO_SECRET_KEY" "$(random_hex)"

echo ""
echo "==> Building Docker images (mysql pulled, backend/admin-frontend/portal-frontend built)..."
docker compose --env-file "${ENV_FILE}" -f "${SCRIPT_DIR}/docker-compose.yml" build

echo ""
echo "=============================================="
echo "Build complete!"
echo "=============================================="
echo ""
echo "Start the ecosystem with:"
echo "  cd docker && docker compose up -d"
echo ""
echo "Ports (see docker/.env to change):"
BACKEND_PORT="$(grep -E '^BACKEND_PORT=' "${ENV_FILE}" | cut -d'=' -f2-)"
ADMIN_FRONTEND_PORT="$(grep -E '^ADMIN_FRONTEND_PORT=' "${ENV_FILE}" | cut -d'=' -f2-)"
PORTAL_FRONTEND_PORT="$(grep -E '^PORTAL_FRONTEND_PORT=' "${ENV_FILE}" | cut -d'=' -f2-)"
echo "  Backend API:      http://localhost:${BACKEND_PORT:-8000}/api/"
echo "  Admin frontend:   http://localhost:${ADMIN_FRONTEND_PORT:-5173}"
echo "  Portal frontend:  http://localhost:${PORTAL_FRONTEND_PORT:-5174}"
echo ""
echo "The API key required for backend requests is stored in docker/.env (API_KEY)."
echo "The MySQL 'admin' user and Django superuser both use the credentials in docker/.env."
echo "=============================================="
