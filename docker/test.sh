#!/bin/bash
# =============================================================================
# Build + deploy smoke test for the HRD System Docker stack.
# =============================================================================
# Runs an *isolated* Compose project so a live `./deploy.sh` stack and its
# MySQL volume (`hrd-system-db`) are left untouched.
#
# What it does:
#   1. Builds images (same Dockerfiles as production)
#   2. Starts mysql + backend + admin-frontend + portal-frontend
#   3. Waits until the backend can serve /api (migrations + seed finished)
#   4. Hits healthz, SPA, API-key, login, /me, and lokasi through the nginx
#      proxies — the same path a browser uses
#   5. Tears the test stack down (including the test volume)
#
# Usage:
#   ./test.sh                 # build, deploy, test, tear down
#   ./test.sh --skip-build    # reuse already-built test images
#   ./test.sh --keep          # leave the test stack running on test ports
#   ./test.sh --help
#
# Test ports (override with env if they collide):
#   TEST_BACKEND_PORT          default 18028
#   TEST_ADMIN_FRONTEND_PORT   default 15128
#   TEST_PORTAL_FRONTEND_PORT  default 15129
#
# Seeded login used for API checks: karyawan_id 0000003 / password 123
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

ENV_FILE="${SCRIPT_DIR}/.env"
ENV_EXAMPLE="${SCRIPT_DIR}/.env.example"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"
COMPOSE_TEST_FILE="${SCRIPT_DIR}/docker-compose.test.yml"
COMPOSE_PROJECT_NAME="docker-hrd-system-test"

TEST_BACKEND_PORT="${TEST_BACKEND_PORT:-18028}"
TEST_ADMIN_FRONTEND_PORT="${TEST_ADMIN_FRONTEND_PORT:-15128}"
TEST_PORTAL_FRONTEND_PORT="${TEST_PORTAL_FRONTEND_PORT:-15129}"

SEED_KARYAWAN_ID="0000003"
SEED_PASSWORD="123"
SEED_NAMA="Kenzie Mihardja"
SEED_LOKASI_ID="99"

DO_BUILD=true
DO_KEEP=false
FAILS=0
PASSES=0

usage() {
    sed -n '2,28p' "$0" | sed 's/^# \?//'
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-build)
            DO_BUILD=false
            shift
            ;;
        --keep)
            DO_KEEP=true
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

# Shell env wins over docker/.env for Compose interpolation — this is how
# the test stack binds 15128/15129/18028 instead of the live 5128/5129/8028.
export BACKEND_PORT="${TEST_BACKEND_PORT}"
export ADMIN_FRONTEND_PORT="${TEST_ADMIN_FRONTEND_PORT}"
export PORTAL_FRONTEND_PORT="${TEST_PORTAL_FRONTEND_PORT}"
export COMPOSE_PROJECT_NAME

RED="$(printf '\033[31m')"
GREEN="$(printf '\033[32m')"
YELLOW="$(printf '\033[33m')"
RESET="$(printf '\033[0m')"

pass() {
    PASSES=$((PASSES + 1))
    echo "  ${GREEN}PASS${RESET}  $1"
}

fail() {
    FAILS=$((FAILS + 1))
    echo "  ${RED}FAIL${RESET}  $1"
}

info() {
    echo "==> $1"
}

die() {
    echo "${RED}Error:${RESET} $1" >&2
    exit 1
}

require_cmd() {
    command -v "$1" &>/dev/null || die "$1 is not installed."
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

compose() {
    docker compose \
        -p "${COMPOSE_PROJECT_NAME}" \
        --env-file "${ENV_FILE}" \
        -f "${COMPOSE_FILE}" \
        -f "${COMPOSE_TEST_FILE}" \
        "$@"
}

# POST/GET helper. Sets HTTP_CODE and CURL_BODY in this shell (not a subshell —
# never capture this function with $(), or CURL_BODY is lost).
HTTP_CODE=""
CURL_BODY=""
curl_status() {
    local method="$1"
    local url="$2"
    shift 2
    local tmp curl_rc
    tmp="$(mktemp)"
    set +e
    HTTP_CODE="$(curl -sS -o "${tmp}" -w '%{http_code}' --connect-timeout 3 --max-time 30 \
        -X "${method}" "${url}" "$@" 2>/dev/null)"
    curl_rc=$?
    set -e
    if [ "${curl_rc}" -ne 0 ]; then
        HTTP_CODE="000"
        CURL_BODY=""
    else
        CURL_BODY="$(cat "${tmp}")"
    fi
    rm -f "${tmp}"
}

json_get() {
    local path="$1"
    python3 -c '
import json, sys
path = sys.argv[1].split(".")
data = json.load(sys.stdin)
for key in path:
    if isinstance(data, list):
        data = data[int(key)]
    else:
        data = data[key]
if data is None:
    raise SystemExit(1)
print(data)
' "${path}"
}

json_has_lokasi_id() {
    local want="$1"
    python3 -c '
import json, sys
want = sys.argv[1]
data = json.load(sys.stdin)
rows = data if isinstance(data, list) else data.get("results", [])
if not isinstance(rows, list):
    raise SystemExit(1)
raise SystemExit(0 if any(str(row.get("id", "")) == want for row in rows) else 1)
' "${want}"
}

port_in_use() {
    local port="$1"
    if command -v ss &>/dev/null; then
        ss -ltn 2>/dev/null | grep -qE ":${port}[[:space:]]"
        return $?
    fi
    if command -v netstat &>/dev/null; then
        netstat -ltn 2>/dev/null | grep -qE ":${port}[[:space:]]"
        return $?
    fi
    return 1
}

cleanup() {
    if [ "${DO_KEEP}" = true ]; then
        echo ""
        info "Leaving test stack running (--keep)."
        echo "  Admin:   http://localhost:${TEST_ADMIN_FRONTEND_PORT}"
        echo "  Portal:  http://localhost:${TEST_PORTAL_FRONTEND_PORT}"
        echo "  Backend: http://localhost:${TEST_BACKEND_PORT}/api/"
        echo "  Stop:    (cd docker && docker compose -p ${COMPOSE_PROJECT_NAME} --env-file .env -f docker-compose.yml -f docker-compose.test.yml down -v)"
        return
    fi
    echo ""
    info "Tearing down test stack (containers + hrd-system-db-test volume)..."
    compose down -v --remove-orphans >/dev/null 2>&1 || true
}

trap cleanup EXIT

# --- preflight ---------------------------------------------------------------
require_cmd docker
require_cmd curl
require_cmd python3

if ! docker info &>/dev/null; then
    die "Docker daemon is not running."
fi
if ! docker compose version &>/dev/null; then
    die "Docker Compose plugin is not available."
fi
if [ ! -f "${COMPOSE_TEST_FILE}" ]; then
    die "missing ${COMPOSE_TEST_FILE}"
fi

for port in "${TEST_BACKEND_PORT}" "${TEST_ADMIN_FRONTEND_PORT}" "${TEST_PORTAL_FRONTEND_PORT}"; do
    if port_in_use "${port}"; then
        die "port ${port} is already in use. Set TEST_BACKEND_PORT / TEST_ADMIN_FRONTEND_PORT / TEST_PORTAL_FRONTEND_PORT."
    fi
done

if [ ! -f "${ENV_FILE}" ]; then
    if [ ! -f "${ENV_EXAMPLE}" ]; then
        die "neither docker/.env nor docker/.env.example found."
    fi
    info "Creating docker/.env from .env.example..."
    cp "${ENV_EXAMPLE}" "${ENV_FILE}"
fi

ensure_env_var "API_KEY" "$(random_hex)"
ensure_env_var "DJANGO_SECRET_KEY" "$(random_hex)"

API_KEY="$(env_value API_KEY)"
if [ -z "${API_KEY}" ]; then
    die "API_KEY is empty in docker/.env."
fi

# Same migration-file check as build.sh — fail fast before a long image build.
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
        die "missing backend/${req} — run: cd backend && python manage.py makemigrations"
    fi
done

ADMIN_URL="http://127.0.0.1:${TEST_ADMIN_FRONTEND_PORT}"
PORTAL_URL="http://127.0.0.1:${TEST_PORTAL_FRONTEND_PORT}"
BACKEND_URL="http://127.0.0.1:${TEST_BACKEND_PORT}"

echo ""
echo "=============================================="
echo "HRD System Docker smoke test"
echo "=============================================="
echo "Project:  ${COMPOSE_PROJECT_NAME}"
echo "Volume:   hrd-system-db-test"
echo "Ports:    admin ${TEST_ADMIN_FRONTEND_PORT}  portal ${TEST_PORTAL_FRONTEND_PORT}  backend ${TEST_BACKEND_PORT}"
echo "Build:    ${DO_BUILD}"
echo ""

# --- build -------------------------------------------------------------------
if [ "${DO_BUILD}" = true ]; then
    info "Building images for project ${COMPOSE_PROJECT_NAME}..."
    compose build
    echo ""
else
    info "Skipping image build (--skip-build)."
    for img in \
        "${COMPOSE_PROJECT_NAME}-backend" \
        "${COMPOSE_PROJECT_NAME}-admin-frontend" \
        "${COMPOSE_PROJECT_NAME}-portal-frontend"
    do
        if ! docker image inspect "${img}" &>/dev/null; then
            die "local image '${img}' not found. Re-run without --skip-build."
        fi
    done
fi

# --- deploy ------------------------------------------------------------------
info "Starting test stack..."
compose up -d --remove-orphans
echo ""

info "Waiting for backend (migrations + seed + gunicorn, up to 3 minutes)..."
READY=false
for attempt in $(seq 1 90); do
    curl_status POST "${BACKEND_URL}/api/admin/login/" \
        -H 'Content-Type: application/json' \
        -H "X-Api-Key: ${API_KEY}" \
        -d '{"karyawan_id":"x","password":"x"}'
    if [ "${HTTP_CODE}" = "401" ] && echo "${CURL_BODY}" | grep -q 'invalid_username'; then
        READY=true
        echo "    backend ready after ~$((attempt * 2))s"
        break
    fi
    sleep 2
done

if [ "${READY}" != true ]; then
    echo "    last HTTP ${HTTP_CODE:-000}: ${CURL_BODY:-(no body)}"
    echo ""
    compose ps || true
    echo ""
    echo "${YELLOW}----- last 80 lines of test-stack logs -----${RESET}"
    compose logs --tail=80 || true
    die "backend did not become ready in time."
fi

# --- assertions --------------------------------------------------------------
echo ""
info "Running smoke tests..."
echo ""

set +e

# Containers should be running, not restarting.
running_count="$(compose ps --status running --format '{{.Name}}' 2>/dev/null | wc -l | tr -d ' ')"
if [ "${running_count}" -ge 4 ]; then
    pass "all 4 services running (${running_count} containers)"
else
    fail "expected 4 running containers, got ${running_count}"
    compose ps
fi

# Frontend healthz
curl_status GET "${ADMIN_URL}/healthz"
health_body="$(printf '%s' "${CURL_BODY}" | tr -d '\r\n')"
if [ "${HTTP_CODE}" = "200" ] && [ "${health_body}" = "ok" ]; then
    pass "admin frontend GET /healthz → 200"
else
    fail "admin frontend GET /healthz → HTTP ${HTTP_CODE} body=${CURL_BODY}"
fi

curl_status GET "${PORTAL_URL}/healthz"
health_body="$(printf '%s' "${CURL_BODY}" | tr -d '\r\n')"
if [ "${HTTP_CODE}" = "200" ] && [ "${health_body}" = "ok" ]; then
    pass "portal frontend GET /healthz → 200"
else
    fail "portal frontend GET /healthz → HTTP ${HTTP_CODE} body=${CURL_BODY}"
fi

# SPA index
curl_status GET "${ADMIN_URL}/"
if [ "${HTTP_CODE}" = "200" ] && echo "${CURL_BODY}" | grep -qiE '<html|<!doctype'; then
    pass "admin frontend serves SPA HTML"
else
    fail "admin frontend GET / → HTTP ${HTTP_CODE} (expected HTML)"
fi

curl_status GET "${PORTAL_URL}/"
if [ "${HTTP_CODE}" = "200" ] && echo "${CURL_BODY}" | grep -qiE '<html|<!doctype'; then
    pass "portal frontend serves SPA HTML"
else
    fail "portal frontend GET / → HTTP ${HTTP_CODE} (expected HTML)"
fi

# API key enforced on the backend port (no nginx injection).
curl_status POST "${BACKEND_URL}/api/admin/login/" \
    -H 'Content-Type: application/json' \
    -d '{"karyawan_id":"0000003","password":"123"}'
if [ "${HTTP_CODE}" = "401" ] && echo "${CURL_BODY}" | grep -q 'Invalid or missing API key'; then
    pass "backend rejects requests without X-Api-Key (HTTP 401)"
else
    fail "backend without API key → HTTP ${HTTP_CODE} body=${CURL_BODY} (expected 401 API key)"
fi

# Admin login through nginx proxy (browser path).
curl_status POST "${ADMIN_URL}/api/admin/login/" \
    -H 'Content-Type: application/json' \
    -d "{\"karyawan_id\":\"${SEED_KARYAWAN_ID}\",\"password\":\"${SEED_PASSWORD}\"}"
ADMIN_TOKEN=""
ADMIN_NAMA=""
if [ "${HTTP_CODE}" = "200" ]; then
    ADMIN_TOKEN="$(echo "${CURL_BODY}" | json_get token 2>/dev/null)"
    ADMIN_NAMA="$(echo "${CURL_BODY}" | json_get karyawan.nama 2>/dev/null)"
fi
if [ "${HTTP_CODE}" = "200" ] && [ -n "${ADMIN_TOKEN}" ] && [ "${ADMIN_NAMA}" = "${SEED_NAMA}" ]; then
    pass "admin login via proxy (0000003) → token + ${SEED_NAMA}"
else
    fail "admin login via proxy → HTTP ${HTTP_CODE} body=${CURL_BODY}"
fi

# Portal login through nginx proxy.
curl_status POST "${PORTAL_URL}/api/portal/login/" \
    -H 'Content-Type: application/json' \
    -d "{\"karyawan_id\":\"${SEED_KARYAWAN_ID}\",\"password\":\"${SEED_PASSWORD}\"}"
PORTAL_TOKEN=""
if [ "${HTTP_CODE}" = "200" ]; then
    PORTAL_TOKEN="$(echo "${CURL_BODY}" | json_get token 2>/dev/null)"
fi
if [ "${HTTP_CODE}" = "200" ] && [ -n "${PORTAL_TOKEN}" ]; then
    pass "portal login via proxy (0000003) → token"
else
    fail "portal login via proxy → HTTP ${HTTP_CODE} body=${CURL_BODY}"
fi

# Authenticated /me
if [ -n "${ADMIN_TOKEN}" ]; then
    curl_status GET "${ADMIN_URL}/api/admin/me/" \
        -H "Authorization: Token ${ADMIN_TOKEN}"
    me_id="$(echo "${CURL_BODY}" | json_get karyawan_id 2>/dev/null)"
    if [ "${HTTP_CODE}" = "200" ] && [ "${me_id}" = "${SEED_KARYAWAN_ID}" ]; then
        pass "GET /api/admin/me/ via proxy → ${SEED_KARYAWAN_ID}"
    else
        fail "GET /api/admin/me/ → HTTP ${HTTP_CODE} body=${CURL_BODY}"
    fi
else
    fail "GET /api/admin/me/ skipped (no admin token)"
fi

if [ -n "${PORTAL_TOKEN}" ]; then
    curl_status GET "${PORTAL_URL}/api/portal/me/" \
        -H "Authorization: Token ${PORTAL_TOKEN}"
    me_id="$(echo "${CURL_BODY}" | json_get karyawan_id 2>/dev/null)"
    if [ "${HTTP_CODE}" = "200" ] && [ "${me_id}" = "${SEED_KARYAWAN_ID}" ]; then
        pass "GET /api/portal/me/ via proxy → ${SEED_KARYAWAN_ID}"
    else
        fail "GET /api/portal/me/ → HTTP ${HTTP_CODE} body=${CURL_BODY}"
    fi
else
    fail "GET /api/portal/me/ skipped (no portal token)"
fi

# Lokasi table exists and seed HQ row is present (catches missing migrations).
if [ -n "${ADMIN_TOKEN}" ]; then
    curl_status GET "${ADMIN_URL}/api/admin/lokasi/" \
        -H "Authorization: Token ${ADMIN_TOKEN}"
    if [ "${HTTP_CODE}" = "200" ] && echo "${CURL_BODY}" | json_has_lokasi_id "${SEED_LOKASI_ID}"; then
        pass "GET /api/admin/lokasi/ includes seeded HQ (${SEED_LOKASI_ID})"
    else
        fail "GET /api/admin/lokasi/ → HTTP ${HTTP_CODE} body=${CURL_BODY}"
    fi
else
    fail "GET /api/admin/lokasi/ skipped (no admin token)"
fi

# Django admin page on the backend port (no API key required).
curl_status GET "${BACKEND_URL}/django-admin/login/"
if [ "${HTTP_CODE}" = "200" ] && echo "${CURL_BODY}" | grep -qi 'Django'; then
    pass "Django admin login page → 200"
else
    fail "GET /django-admin/login/ → HTTP ${HTTP_CODE}"
fi

set -e

echo ""
echo "=============================================="
if [ "${FAILS}" -eq 0 ]; then
    echo "${GREEN}All ${PASSES} checks passed.${RESET}"
    echo "=============================================="
    exit 0
fi

echo "${RED}${FAILS} check(s) failed, ${PASSES} passed.${RESET}"
echo "=============================================="
echo ""
compose ps || true
echo ""
echo "${YELLOW}----- last 80 lines of test-stack logs -----${RESET}"
compose logs --tail=80 || true
exit 1
