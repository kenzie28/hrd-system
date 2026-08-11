#!/bin/bash
# =============================================================================
# Deploy (start) the HRD System Docker Compose stack.
# =============================================================================
# Brings up mysql, backend, admin-frontend, and portal-frontend as containers.
# Ensures docker/.env exists and has required secrets (API_KEY,
# DJANGO_SECRET_KEY) the same way ./build.sh does.
#
# Usage:
#   ./deploy.sh              # start (or recreate) the stack
#   ./deploy.sh --build      # rebuild images, then start
#   ./deploy.sh --down       # stop and remove containers (keeps mysql volume)
#   ./deploy.sh --restart    # restart running containers
#   ./deploy.sh --status     # show container status
#   ./deploy.sh --logs       # follow logs (Ctrl+C to stop)
#   ./deploy.sh --help
#
# Prerequisites: Docker with Compose plugin available.
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

ENV_FILE="${SCRIPT_DIR}/.env"
ENV_EXAMPLE="${SCRIPT_DIR}/.env.example"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"

DO_BUILD=false
DO_DOWN=false
DO_RESTART=false
DO_STATUS=false
DO_LOGS=false

usage() {
    sed -n '2,20p' "$0" | sed 's/^# \?//'
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --build|-b)
            DO_BUILD=true
            shift
            ;;
        --down|-d)
            DO_DOWN=true
            shift
            ;;
        --restart|-r)
            DO_RESTART=true
            shift
            ;;
        --status|-s)
            DO_STATUS=true
            shift
            ;;
        --logs|-l)
            DO_LOGS=true
            shift
            ;;
        --help|-h)
            usage
            ;;
        -*)
            echo "Unknown option: $1"
            echo "Use --help for usage."
            exit 1
            ;;
        *)
            echo "Error: unexpected argument: $1"
            echo "Use --help for usage."
            exit 1
            ;;
    esac
done

if ! command -v docker &>/dev/null; then
    echo "Error: docker is not installed."
    exit 1
fi

if ! docker info &>/dev/null; then
    echo "Error: Docker daemon is not running."
    exit 1
fi

if ! docker compose version &>/dev/null; then
    echo "Error: Docker Compose plugin is not available."
    echo "Install it or upgrade Docker Desktop / docker-compose-plugin."
    exit 1
fi

compose() {
    docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
}

env_value() {
    local key="$1"
    local default="${2:-}"
    local value=""
    if [ -f "${ENV_FILE}" ]; then
        value="$(grep -E "^${key}=" "${ENV_FILE}" | head -n1 | cut -d'=' -f2-)"
    fi
    echo "${value:-${default}}"
}

print_urls() {
    local backend_port admin_port portal_port
    backend_port="$(env_value BACKEND_PORT 8028)"
    admin_port="$(env_value ADMIN_FRONTEND_PORT 5128)"
    portal_port="$(env_value PORTAL_FRONTEND_PORT 5129)"

    echo ""
    echo "=============================================="
    echo "Deploy complete!"
    echo "=============================================="
    echo ""
    echo "Open these URLs from this machine (or use this host's IP/domain):"
    echo "  Admin frontend:   http://localhost:${admin_port}"
    echo "  Portal frontend:  http://localhost:${portal_port}"
    echo "  Backend API:      http://localhost:${backend_port}/api/"
    echo "  Django admin:     http://localhost:${backend_port}/django-admin/"
    echo ""
    echo "Browsers call same-origin /api on the frontend ports;"
    echo "nginx proxies to the backend and injects API_KEY automatically."
    echo ""
    echo "HR admin login (auto-seeded on backend start):"
    echo "  karyawan_id: 0000003"
    echo "  name:        Kenzie Mihardja"
    echo "  password:    123  (change on first login)"
    echo ""
    echo "Secrets: docker/.env (API_KEY, DB, Django superuser)"
    echo ""
    echo "Useful commands:"
    echo "  ./deploy.sh --status"
    echo "  ./deploy.sh --logs"
    echo "  ./deploy.sh --down"
    echo "=============================================="
}

# --- status / logs do not need full env bootstrap beyond .env existence ---
if [ "${DO_STATUS}" = true ]; then
    if [ ! -f "${ENV_FILE}" ]; then
        echo "Error: docker/.env not found. Run ./deploy.sh or ./build.sh first."
        exit 1
    fi
    compose ps
    exit 0
fi

if [ "${DO_LOGS}" = true ]; then
    if [ ! -f "${ENV_FILE}" ]; then
        echo "Error: docker/.env not found. Run ./deploy.sh or ./build.sh first."
        exit 1
    fi
    compose logs -f
    exit 0
fi

if [ "${DO_DOWN}" = true ]; then
    if [ ! -f "${ENV_FILE}" ]; then
        echo "Error: docker/.env not found. Nothing to stop."
        exit 1
    fi
    echo "==> Stopping HRD System containers..."
    compose down
    echo "Containers stopped. MySQL data volume was kept."
    exit 0
fi

if [ "${DO_RESTART}" = true ]; then
    if [ ! -f "${ENV_FILE}" ]; then
        echo "Error: docker/.env not found. Run ./deploy.sh or ./build.sh first."
        exit 1
    fi
    echo "==> Restarting HRD System containers..."
    compose restart
    compose ps
    print_urls
    exit 0
fi

# --- full deploy path ---
if [ ! -f "${ENV_FILE}" ]; then
    if [ ! -f "${ENV_EXAMPLE}" ]; then
        echo "Error: neither docker/.env nor docker/.env.example found."
        exit 1
    fi
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

# Sets KEY to VALUE in .env only if KEY is missing or blank.
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

if [ "${DO_BUILD}" = true ]; then
    echo "==> Rebuilding images..."
    "${SCRIPT_DIR}/build.sh"
    echo ""
else
    # Build only if local images for the compose project are missing.
    COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-docker}"
    NEED_BUILD=false
    for img in \
        "${COMPOSE_PROJECT_NAME}-backend" \
        "${COMPOSE_PROJECT_NAME}-admin-frontend" \
        "${COMPOSE_PROJECT_NAME}-portal-frontend"
    do
        if ! docker image inspect "${img}" &>/dev/null; then
            NEED_BUILD=true
            break
        fi
    done

    if [ "${NEED_BUILD}" = true ]; then
        echo "==> Local images not found; building once via ./build.sh..."
        "${SCRIPT_DIR}/build.sh"
        echo ""
    fi
fi

echo "=============================================="
echo "Deploying HRD System"
echo "=============================================="
echo ""

echo "==> Starting containers (docker compose up -d)..."
compose up -d --remove-orphans

echo ""
echo "==> Waiting for services to become healthy..."
# Give mysql healthcheck + backend migrations a moment, then show status.
sleep 3
compose ps

print_urls
