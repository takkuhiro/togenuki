#!/bin/bash
# Cloud Run Image Update Script for TogeNuki Web Frontend
# Usage: ./deploy.sh
#
# This script builds and deploys a new Docker image to Cloud Run.
# Infrastructure (Cloud Run service itself) is managed by Terraform.
#
# Required: .env file with Firebase configuration or environment variables:
#   VITE_FIREBASE_API_KEY
#   VITE_FIREBASE_AUTH_DOMAIN
#   VITE_FIREBASE_PROJECT_ID
#   VITE_FIREBASE_STORAGE_BUCKET
#   VITE_FIREBASE_MESSAGING_SENDER_ID
#   VITE_FIREBASE_APP_ID

set -e

# Load .env file if exists
if [ -f ".env" ]; then
    echo "Loading .env file..."
    export $(grep -v '^#' .env | xargs)
fi

# Configuration
PROJECT_ID="${PROJECT_ID:-aitech-good-s15112}"
REGION="${REGION:-asia-northeast1}"
SERVICE_NAME="${SERVICE_NAME:-togenuki-web}"
REPOSITORY="${REPOSITORY:-togenuki}"

# Artifact Registry image URL
IMAGE_URL="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${SERVICE_NAME}"
TAG="${TAG:-latest}"
FULL_IMAGE="${IMAGE_URL}:${TAG}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== TogeNuki Web Image Update ===${NC}"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo "Image: ${FULL_IMAGE}"
echo ""

# Check required Firebase environment variables
REQUIRED_VARS=(
    "VITE_FIREBASE_API_KEY"
    "VITE_FIREBASE_AUTH_DOMAIN"
    "VITE_FIREBASE_PROJECT_ID"
    "VITE_FIREBASE_APP_ID"
)

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo -e "${RED}Error: ${var} is not set${NC}"
        echo "Please set Firebase environment variables or create .env file"
        echo ""
        echo "Example .env:"
        echo "  VITE_FIREBASE_API_KEY=your-api-key"
        echo "  VITE_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com"
        echo "  VITE_FIREBASE_PROJECT_ID=your-project-id"
        echo "  VITE_FIREBASE_STORAGE_BUCKET=your-project.appspot.com"
        echo "  VITE_FIREBASE_MESSAGING_SENDER_ID=123456789"
        echo "  VITE_FIREBASE_APP_ID=1:123456789:web:abc123"
        exit 1
    fi
done

echo -e "${GREEN}Firebase config found${NC}"

# Step 1: Configure Docker for Artifact Registry
echo -e "${YELLOW}Step 1: Configuring Docker authentication...${NC}"
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

# Step 2: Build Docker image (amd64 for Cloud Run)
echo -e "${YELLOW}Step 2: Building Docker image (linux/amd64)...${NC}"
docker build --platform linux/amd64 \
    --build-arg VITE_FIREBASE_API_KEY="${VITE_FIREBASE_API_KEY}" \
    --build-arg VITE_FIREBASE_AUTH_DOMAIN="${VITE_FIREBASE_AUTH_DOMAIN}" \
    --build-arg VITE_FIREBASE_PROJECT_ID="${VITE_FIREBASE_PROJECT_ID}" \
    --build-arg VITE_FIREBASE_STORAGE_BUCKET="${VITE_FIREBASE_STORAGE_BUCKET}" \
    --build-arg VITE_FIREBASE_MESSAGING_SENDER_ID="${VITE_FIREBASE_MESSAGING_SENDER_ID}" \
    --build-arg VITE_FIREBASE_APP_ID="${VITE_FIREBASE_APP_ID}" \
    -t "${FULL_IMAGE}" .

# Step 3: Push to Artifact Registry
echo -e "${YELLOW}Step 3: Pushing image to Artifact Registry...${NC}"
docker push "${FULL_IMAGE}"

# Step 4: Deploy new image to Cloud Run
echo -e "${YELLOW}Step 4: Updating Cloud Run service with new image...${NC}"
gcloud run services update "${SERVICE_NAME}" \
    --image "${FULL_IMAGE}" \
    --platform managed \
    --region "${REGION}" \
    --project "${PROJECT_ID}"

# Step 5: Get the service URL
echo -e "${YELLOW}Step 5: Getting service URL...${NC}"
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --platform managed \
    --region "${REGION}" \
    --project "${PROJECT_ID}" \
    --format "value(status.url)")

echo ""
echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo -e "Service URL: ${GREEN}${SERVICE_URL}${NC}"
echo ""
echo "Test endpoints:"
echo "  Health: curl ${SERVICE_URL}/health"
echo "  App:    ${SERVICE_URL}/"
