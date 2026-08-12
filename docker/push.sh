#!/bin/bash
# =============================================================================
# Tag and push HRD System images to Docker Hub.
# =============================================================================
# Prerequisites:
#   1. Build images first:  ./build.sh
#   2. Log in to Docker Hub: docker login
#   3. Set DOCKERHUB_USERNAME in docker/.env (or export it)
#
# Usage:
#   ./push.sh                 # push as :latest
#   ./push.sh 1.0.0           # push as :1.0.0 and :latest
#   ./push.sh --build 1.0.0   # rebuild first, then push
#
# Docker Hub repos created/used (under your username):
#   hrd-backend
#   hrd-admin-frontend
#   hrd-portal-frontend
#
# MySQL is pulled from the public mysql:8.0 image and is not pushed.
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

ENV_FILE="${SCRIPT_DIR}/.env"

# Load docker/.env if present (values already in the environment win).
if [ -f "${ENV_FILE}" ]; then
    set -a
    # shellcheck disable=SC1090
    source "${ENV_FILE}"
    set +a
fi

# Compose names images as <project>-<service>. Project name is the directory
# name unless overridden in COMPOSE_PROJECT_NAME.
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-docker-hrd-system}"
LOCAL_BACKEND="${COMPOSE_PROJECT_NAME}-backend"
LOCAL_ADMIN="${COMPOSE_PROJECT_NAME}-admin-frontend"
LOCAL_PORTAL="${COMPOSE_PROJECT_NAME}-portal-frontend"

IMAGE_PREFIX="${IMAGE_PREFIX:-hrd}"
TAG_VERSION=""
DO_BUILD=false

usage() {
    sed -n '2,22p' "$0" | sed 's/^# \?//'
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --build|-b)
            DO_BUILD=true
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
            if [ -n "${TAG_VERSION}" ]; then
                echo "Error: unexpected extra argument: $1"
                exit 1
            fi
            TAG_VERSION="$1"
            shift
            ;;
    esac
done

if [ -z "${DOCKERHUB_USERNAME}" ]; then
    echo "Error: DOCKERHUB_USERNAME is not set."
    echo ""
    echo "Add it to docker/.env:"
    echo "  DOCKERHUB_USERNAME=your-dockerhub-username"
    echo ""
    echo "Or export it:"
    echo "  export DOCKERHUB_USERNAME=your-dockerhub-username"
    exit 1
fi

if ! command -v docker &>/dev/null; then
    echo "Error: docker is not installed."
    exit 1
fi

if ! docker info &>/dev/null; then
    echo "Error: Docker daemon is not running."
    exit 1
fi

# docker login stores auth in ~/.docker/config.json — require a Docker Hub entry.
if [ ! -f "${HOME}/.docker/config.json" ] || ! grep -qE 'https://index\.docker\.io|docker\.io' "${HOME}/.docker/config.json" 2>/dev/null; then
    echo "Warning: no Docker Hub credentials found in ~/.docker/config.json."
    echo "If the push fails, run:  docker login"
    echo ""
fi

if [ "${DO_BUILD}" = true ]; then
    echo "==> Rebuilding images first..."
    "${SCRIPT_DIR}/build.sh"
    echo ""
fi

require_local_image() {
    local name="$1"
    if ! docker image inspect "${name}" &>/dev/null; then
        echo "Error: local image '${name}' not found."
        echo "Build first with: ./build.sh"
        echo "Or re-run with:    ./push.sh --build"
        exit 1
    fi
}

require_local_image "${LOCAL_BACKEND}"
require_local_image "${LOCAL_ADMIN}"
require_local_image "${LOCAL_PORTAL}"

REMOTE_BACKEND="${DOCKERHUB_USERNAME}/${IMAGE_PREFIX}-backend"
REMOTE_ADMIN="${DOCKERHUB_USERNAME}/${IMAGE_PREFIX}-admin-frontend"
REMOTE_PORTAL="${DOCKERHUB_USERNAME}/${IMAGE_PREFIX}-portal-frontend"

# Always push :latest; optionally also a version tag.
TAGS=("latest")
if [ -n "${TAG_VERSION}" ]; then
    TAGS=("${TAG_VERSION}" "latest")
fi

echo "=============================================="
echo "Push HRD System images to Docker Hub"
echo "=============================================="
echo "Docker Hub user: ${DOCKERHUB_USERNAME}"
echo "Image prefix:    ${IMAGE_PREFIX}"
echo "Tags:            ${TAGS[*]}"
echo ""
echo "Will push:"
echo "  ${REMOTE_BACKEND}"
echo "  ${REMOTE_ADMIN}"
echo "  ${REMOTE_PORTAL}"
echo ""

tag_and_push() {
    local local_image="$1"
    local remote_base="$2"
    local tag="$3"
    local remote="${remote_base}:${tag}"

    echo "==> Tagging  ${local_image}  →  ${remote}"
    docker tag "${local_image}" "${remote}"
    echo "==> Pushing  ${remote}"
    docker push "${remote}"
    echo ""
}

for tag in "${TAGS[@]}"; do
    tag_and_push "${LOCAL_BACKEND}" "${REMOTE_BACKEND}" "${tag}"
    tag_and_push "${LOCAL_ADMIN}" "${REMOTE_ADMIN}" "${tag}"
    tag_and_push "${LOCAL_PORTAL}" "${REMOTE_PORTAL}" "${tag}"
done

echo "=============================================="
echo "Push complete!"
echo "=============================================="
echo ""
echo "Images:"
for tag in "${TAGS[@]}"; do
    echo "  docker pull ${REMOTE_BACKEND}:${tag}"
    echo "  docker pull ${REMOTE_ADMIN}:${tag}"
    echo "  docker pull ${REMOTE_PORTAL}:${tag}"
    echo ""
done
echo "Make sure these Docker Hub repositories exist (or are auto-created)"
echo "and are public/private as you intend under your account."
echo "=============================================="
