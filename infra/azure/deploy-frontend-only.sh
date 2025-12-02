#!/bin/bash

# Frontend-Only Deployment Script for Prism
# Usage: ./deploy-frontend-only.sh [environment]
# Environment: dev, staging, prod (default: dev)

set -e  # Exit on error

# Configuration
ENVIRONMENT=${1:-dev}
RESOURCE_GROUP="rg-prism-${ENVIRONMENT}"
ACR_NAME="acrprism${ENVIRONMENT}"
FRONTEND_APP="prism-frontend-${ENVIRONMENT}"
BACKEND_APP="prism-backend-${ENVIRONMENT}"
BUILD_TAG="build-$(date +%s)"

echo "🚀 Deploying Frontend Only to Azure Container Apps"
echo "Environment: ${ENVIRONMENT}"
echo "Resource Group: ${RESOURCE_GROUP}"
echo ""

# Check if logged in to Azure
echo "📋 Checking Azure CLI authentication..."
az account show > /dev/null 2>&1 || {
    echo "❌ Not logged in to Azure. Run 'az login' first."
    exit 1
}

# Check if .env file exists
if [ ! -f "../../.env" ]; then
    echo "❌ Error: .env file not found at project root"
    echo "Please create a .env file with required Azure credentials"
    exit 1
fi

# Load environment variables from .env
echo "📋 Loading environment variables from .env..."
export $(cat ../../.env | grep -v '^#' | grep -v '^\s*$' | xargs)

# Login to ACR
echo "🔑 Logging in to ACR..."
az acr login --name $ACR_NAME || true  # Ignore Docker Desktop warnings on WSL

# Get current backend URL (so frontend can connect to it)
echo "🔍 Getting backend URL..."
BACKEND_FQDN=$(az containerapp show \
    --name $BACKEND_APP \
    --resource-group $RESOURCE_GROUP \
    --query properties.configuration.ingress.fqdn -o tsv 2>/dev/null)

if [ -z "$BACKEND_FQDN" ]; then
    echo "❌ Backend not found. Deploy full stack first using deploy.sh"
    exit 1
fi

echo "Backend URL: https://$BACKEND_FQDN"

# Build and push ONLY frontend
echo "🏗️  Building frontend image..."
cd ../..
docker build \
    --build-arg VITE_API_URL=https://$BACKEND_FQDN \
    -t $ACR_NAME.azurecr.io/prism-frontend:$BUILD_TAG \
    -f apps/web/Dockerfile \
    apps/web/

echo "📦 Pushing frontend image..."
docker push $ACR_NAME.azurecr.io/prism-frontend:$BUILD_TAG

# Update ONLY frontend container app
echo "🚀 Updating frontend container app..."
az containerapp update \
    --name $FRONTEND_APP \
    --resource-group $RESOURCE_GROUP \
    --image $ACR_NAME.azurecr.io/prism-frontend:$BUILD_TAG \
    --revision-suffix "v$(date +%s)" \
    --output none

# Get frontend URL
echo "🔍 Getting frontend URL..."
FRONTEND_URL=$(az containerapp show \
    --name $FRONTEND_APP \
    --resource-group $RESOURCE_GROUP \
    --query properties.configuration.ingress.fqdn -o tsv)

echo ""
echo "✅ Frontend deployment complete!"
echo ""
echo "🌐 Frontend URL: https://$FRONTEND_URL"
echo "🔧 Backend URL: https://$BACKEND_FQDN (unchanged)"
echo ""
echo "📊 View frontend logs:"
echo "  az containerapp logs show --name $FRONTEND_APP --resource-group $RESOURCE_GROUP --follow"
echo ""
