#!/bin/bash
# =============================================================================
# One-Time Google Cloud Setup Script
# =============================================================================
# Run ONCE when setting up a new GCP project for HRD System.
#
# Prerequisites:
# - Google Cloud SDK (gcloud) installed and configured
# - gcloud auth login
# - Appropriate permissions in the GCP project
# =============================================================================

set -e

# Configuration — edit before running
PROJECT_ID="paperclip-478601"
REGION="asia-southeast1"
SERVICE_NAME="hrd-system"
REPOSITORY_NAME="hrd-system"

echo "=============================================="
echo "HRD System - One-Time GCloud Setup"
echo "=============================================="
echo ""
echo "Project ID: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service Name: ${SERVICE_NAME}"
echo ""

if [ "${PROJECT_ID}" = "TODO_insert_YOUR_project_ID" ]; then
    echo "Error: Edit PROJECT_ID in this script before running."
    exit 1
fi

echo "==> Setting active project to ${PROJECT_ID}..."
gcloud config set project "${PROJECT_ID}"

echo ""
echo "==> Enabling required Google Cloud APIs..."
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com

echo "APIs enabled successfully."

echo ""
echo "==> Creating Artifact Registry repository..."
if gcloud artifacts repositories describe "${REPOSITORY_NAME}" --location="${REGION}" >/dev/null 2>&1; then
    echo "Repository '${REPOSITORY_NAME}' already exists. Skipping creation."
else
    gcloud artifacts repositories create "${REPOSITORY_NAME}" \
        --repository-format=docker \
        --location="${REGION}" \
        --description="Docker repository for HRD System"
    echo "Repository created successfully."
fi

echo ""
echo "==> Configuring Docker authentication..."
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo ""
    echo "==> Creating .env from .env.example..."
    cp .env.example .env
    echo "Edit .env with production values before deploying."
fi

echo ""
echo "=============================================="
echo "Setup Complete!"
echo "=============================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Edit .env with production values (DJANGO_SECRET_KEY, etc.)"
echo "2. Edit PROJECT_ID in deploy.sh if not already done"
echo "3. Deploy the application:"
echo "   ./deploy.sh --build --env    # First deploy (build image + set env)"
echo "   ./deploy.sh                  # Redeploy existing image"
echo "   ./deploy.sh --build          # Rebuild image only"
echo "   ./deploy.sh --env            # Update environment variables only"
echo ""
echo "=============================================="
