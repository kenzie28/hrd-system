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
#   ./deploy.sh
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

ENV_FILE="${SCRIPT_DIR}/.env"
ENV_EXAMPLE="${SCRIPT_DIR}/.env.example"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-docker-hrd-system}"

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

# Migrations must exist on the host (and be committed) so `COPY backend/` packs them.
# A .gitignore that excluded **/migrations/*.py caused images that only ran auth/admin
# migrations and then crashed creating core_lokasi.
for req in \
    lokasi/migrations/0001_initial.py \
    karyawan/migrations/0001_initial.py \
    absensi/migrations/0001_initial.py \
    shift/migrations/0001_initial.py \
    cuti/migrations/0001_initial.py \
    gaji/migrations/0001_initial.py \
    lembur/migrations/0001_initial.py \
    liburan/migrations/0001_initial.py
do
    if [ ! -f "${SCRIPT_DIR}/../backend/${req}" ]; then
        echo "Error: missing backend/${req}"
        echo "Run: cd backend && python manage.py makemigrations"
        echo "Then commit migration files (do not gitignore them)."
        exit 1
    fi
done

echo ""
echo "==> Building Docker images (mysql pulled, backend/admin-frontend/portal-frontend built)..."
docker compose -p "${COMPOSE_PROJECT_NAME}" --env-file "${ENV_FILE}" -f "${SCRIPT_DIR}/docker-compose.yml" build

echo ""
echo "=============================================="
echo "Build complete!"
echo "=============================================="
echo ""
echo "Start the ecosystem with:"
echo "  ./deploy.sh"
echo ""
echo "Ports (see docker/.env to change):"
BACKEND_PORT="$(grep -E '^BACKEND_PORT=' "${ENV_FILE}" | cut -d'=' -f2-)"
ADMIN_FRONTEND_PORT="$(grep -E '^ADMIN_FRONTEND_PORT=' "${ENV_FILE}" | cut -d'=' -f2-)"
PORTAL_FRONTEND_PORT="$(grep -E '^PORTAL_FRONTEND_PORT=' "${ENV_FILE}" | cut -d'=' -f2-)"
echo "  Admin frontend:   http://localhost:${ADMIN_FRONTEND_PORT:-5128}"
echo "  Portal frontend:  http://localhost:${PORTAL_FRONTEND_PORT:-5129}"
echo "  Backend API:      http://localhost:${BACKEND_PORT:-8028}/api/"
echo ""
echo "Frontends use same-origin /api; nginx injects API_KEY from docker/.env."
echo "=============================================="
