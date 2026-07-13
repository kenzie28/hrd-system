#!/bin/bash
# =============================================================================
# HRD System Deployment Script
# =============================================================================
# Usage:
#   ./deploy.sh [OPTIONS]
#
# Options:
#   --env, -e       Update environment variables from .env
#   --build, -b     Rebuild and push Docker image
#   --setup, -s     Seed lokasi + admin karyawan on container start
#   --debug, -d     Deploy with debug logging (DJANGO_DEBUG, HRD_DEBUG, verbose gunicorn)
#   --help, -h      Show this help message
#
# Examples:
#   ./deploy.sh                 # Simple redeploy (no rebuild, no env update)
#   ./deploy.sh --build         # Rebuild image and deploy
#   ./deploy.sh --env           # Deploy with updated env variables
#   ./deploy.sh --build --env   # Full deployment with rebuild and env update
#   ./deploy.sh --setup         # Deploy and run initial_setup on container start
#   ./deploy.sh --debug         # Deploy with failure-only debug output in Cloud Run logs
#   ./deploy.sh --build --debug # Rebuild image and deploy in debug mode
# =============================================================================

set -e

# Configuration — edit before running
PROJECT_ID="paperclip-478601"
REGION="asia-southeast1"
SERVICE_NAME="hrd-system"
REPOSITORY_NAME="hrd-system"
IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY_NAME}/${SERVICE_NAME}"
ENV_FILE=".env"

BUILD_IMAGE=false
UPDATE_ENV=false
RUN_SETUP=false
DEBUG_DEPLOY=false

DEBUG_ENV_VARS="DJANGO_DEBUG=true,HRD_DEBUG=true,GUNICORN_LOG_LEVEL=debug"

while [[ $# -gt 0 ]]; do
    case $1 in
        --build|-b)
            BUILD_IMAGE=true
            shift
            ;;
        --env|-e)
            UPDATE_ENV=true
            shift
            ;;
        --setup|-s)
            RUN_SETUP=true
            shift
            ;;
        --debug|-d)
            DEBUG_DEPLOY=true
            shift
            ;;
        --help|-h)
            echo "HRD System Deployment Script"
            echo ""
            echo "Usage: ./deploy.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --env, -e       Update environment variables from .env"
            echo "  --build, -b     Rebuild and push Docker image (requires Docker)"
            echo "  --setup, -s     Seed lokasi + admin karyawan on container start"
            echo "  --debug, -d     Deploy with debug logging (failure diagnostics in Cloud Run logs)"
            echo "  --help, -h      Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./deploy.sh                 # Simple redeploy"
            echo "  ./deploy.sh --build         # Rebuild image and deploy"
            echo "  ./deploy.sh --env           # Deploy with updated env variables"
            echo "  ./deploy.sh --build --env   # Full deployment"
            echo "  ./deploy.sh --setup         # Deploy with initial data seed"
            echo "  ./deploy.sh --debug         # Deploy with debug logging enabled"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "=============================================="
echo "HRD System Deployment"
echo "=============================================="
echo ""
echo "Project ID: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo "Build Image: ${BUILD_IMAGE}"
echo "Update Env: ${UPDATE_ENV}"
echo "Run Setup: ${RUN_SETUP}"
echo "Debug Mode: ${DEBUG_DEPLOY}"
echo ""

if [ "${DEBUG_DEPLOY}" = true ]; then
    echo "==> Debug deploy enabled"
    echo "    DJANGO_DEBUG=true  — Django error pages and verbose errors"
    echo "    HRD_DEBUG=true     — [HRD_DEBUG] lines on failure paths only"
    echo "    GUNICORN_LOG_LEVEL=debug — request-level gunicorn logging"
    echo ""
fi

if [ "${PROJECT_ID}" = "TODO_insert_YOUR_project_ID" ]; then
    echo "Error: Edit PROJECT_ID in this script before running."
    exit 1
fi

echo "==> Committing and pushing changes to Git..."
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
GIT_TIMESTAMP=$(date +"%d-%m-%Y %H:%M")

git add .

if git commit -m "Pre-Deployment Commit ${GIT_TIMESTAMP}"; then
    echo "Changes committed locally."
    echo "==> Pushing to origin ${CURRENT_BRANCH}..."
    git push origin "${CURRENT_BRANCH}"
else
    echo "No changes to commit. Skipping push."
fi

echo "==> Setting active project..."
gcloud config set project "${PROJECT_ID}"

DEPLOY_TAG="latest"

if [ "$BUILD_IMAGE" = true ]; then
    echo ""
    echo "==> Checking Docker availability..."

    if ! command -v docker &> /dev/null; then
        echo ""
        echo "Error: Docker is not installed!"
        echo "Install Docker or use Cloud Build: gcloud builds submit --tag ${IMAGE_NAME}"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        echo ""
        echo "Error: Docker daemon is not running!"
        exit 1
    fi

    echo "Docker is available and running"
    echo ""
    echo "==> Building Docker image..."

    TIMESTAMP=$(date +%Y%m%d-%H%M%S)
    DEPLOY_TAG="${TIMESTAMP}"
    TAGGED_IMAGE="${IMAGE_NAME}:${DEPLOY_TAG}"
    LATEST_IMAGE="${IMAGE_NAME}:latest"

    echo "Building: ${TAGGED_IMAGE}"
    docker build -t "${TAGGED_IMAGE}" -t "${LATEST_IMAGE}" .

    echo ""
    echo "==> Pushing Docker image to Artifact Registry..."
    docker push "${TAGGED_IMAGE}"
    docker push "${LATEST_IMAGE}"

    echo "Image pushed successfully."
    echo "Deploy tag: ${DEPLOY_TAG}"
fi

echo ""
echo "==> Deploying to Cloud Run..."
echo "Using image: ${IMAGE_NAME}:${DEPLOY_TAG}"

DEPLOY_CMD=(gcloud run deploy "${SERVICE_NAME}"
    --image "${IMAGE_NAME}:${DEPLOY_TAG}"
    --platform managed
    --region "${REGION}"
    --allow-unauthenticated
    --port 8080
    --memory 1Gi
    --cpu 1
    --min-instances 1
    --max-instances 5
    --timeout 300
    --concurrency 80
)

if [ "$UPDATE_ENV" = true ]; then
    if [ ! -f "${ENV_FILE}" ]; then
        echo "Error: ${ENV_FILE} not found!"
        echo "Copy .env.example to .env and fill in production values."
        exit 1
    fi

    echo "Loading environment variables from ${ENV_FILE}..."

    ENV_VARS=""
    while IFS= read -r line || [ -n "$line" ]; do
        if [[ "$line" =~ ^#.*$ ]] || [[ -z "$line" ]] || [[ "$line" =~ ^[[:space:]]*$ ]]; then
            continue
        fi
        if [[ ! "$line" =~ = ]]; then
            continue
        fi
        if [ -z "$ENV_VARS" ]; then
            ENV_VARS="$line"
        else
            ENV_VARS="${ENV_VARS},${line}"
        fi
    done < "${ENV_FILE}"

    if [ "$RUN_SETUP" = true ]; then
        if [ -n "$ENV_VARS" ]; then
            ENV_VARS="${ENV_VARS},RUN_INITIAL_SETUP=true"
        else
            ENV_VARS="RUN_INITIAL_SETUP=true"
        fi
    fi

    if [ "$DEBUG_DEPLOY" = true ]; then
        if [ -n "$ENV_VARS" ]; then
            ENV_VARS="${ENV_VARS},${DEBUG_ENV_VARS}"
        else
            ENV_VARS="${DEBUG_ENV_VARS}"
        fi
    fi

    if [ -n "$ENV_VARS" ]; then
        DEPLOY_CMD+=(--set-env-vars "${ENV_VARS}")
    fi
elif [ "$RUN_SETUP" = true ] || [ "$DEBUG_DEPLOY" = true ]; then
    PATCH_ENV_VARS=""
    if [ "$RUN_SETUP" = true ]; then
        PATCH_ENV_VARS="RUN_INITIAL_SETUP=true"
    fi
    if [ "$DEBUG_DEPLOY" = true ]; then
        if [ -n "$PATCH_ENV_VARS" ]; then
            PATCH_ENV_VARS="${PATCH_ENV_VARS},${DEBUG_ENV_VARS}"
        else
            PATCH_ENV_VARS="${DEBUG_ENV_VARS}"
        fi
    fi
    DEPLOY_CMD+=(--update-env-vars "${PATCH_ENV_VARS}")
fi

echo ""
echo "Executing deployment..."
"${DEPLOY_CMD[@]}"

echo ""
echo "==> Fetching service URL..."
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --region "${REGION}" --format='value(status.url)')

echo ""
echo "=============================================="
echo "Deployment Complete!"
echo "=============================================="
echo ""
echo "Service URL: ${SERVICE_URL}"
echo ""
echo "Production URLs:"
echo "  Portal:       ${SERVICE_URL}/portal/"
echo "  HR Admin:     ${SERVICE_URL}/hr/"
echo "  API:          ${SERVICE_URL}/api/"
echo "  Django Admin: ${SERVICE_URL}/django-admin/"
echo ""
echo "To view logs:"
echo "  gcloud run services logs read ${SERVICE_NAME} --region ${REGION}"
echo ""
if [ "$DEBUG_DEPLOY" = true ]; then
    echo "Debug mode is ON. Look for [HRD_DEBUG] lines when imports or API calls fail:"
    echo "  gcloud run services logs read ${SERVICE_NAME} --region ${REGION} | grep HRD_DEBUG"
    echo ""
    echo "Turn off debug after troubleshooting:"
    echo "  gcloud run services update ${SERVICE_NAME} --region ${REGION} \\"
    echo "    --update-env-vars DJANGO_DEBUG=false,HRD_DEBUG=false,GUNICORN_LOG_LEVEL=info"
    echo ""
fi
if [ "$RUN_SETUP" = true ]; then
    echo "Initial setup enabled (RUN_INITIAL_SETUP=true)."
    echo "HR admin login: karyawan_id 0000003, password 123"
    echo "Remove RUN_INITIAL_SETUP after first deploy if you do not want setup on every restart:"
    echo "  gcloud run services update ${SERVICE_NAME} --region ${REGION} --remove-env-vars RUN_INITIAL_SETUP"
    echo ""
fi
echo "=============================================="
