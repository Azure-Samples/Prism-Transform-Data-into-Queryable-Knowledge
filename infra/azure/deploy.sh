#!/bin/bash

# Azure Container Apps Deployment Script for Prism
# Usage: ./deploy.sh [environment]
# Environment: dev, staging, prod (default: dev)

set -e  # Exit on error

# Configuration
ENVIRONMENT=${1:-dev}
RESOURCE_GROUP="rg-prism-${ENVIRONMENT}"
LOCATION="eastus"
ACR_NAME="acrprism${ENVIRONMENT}"
CONTAINER_ENV="env-prism-${ENVIRONMENT}"
BACKEND_APP="prism-backend-${ENVIRONMENT}"
FRONTEND_APP="prism-frontend-${ENVIRONMENT}"
BUILD_TAG="build-$(date +%s)"  # Unique tag for each build

echo "🚀 Deploying Prism to Azure Container Apps"
echo "Environment: ${ENVIRONMENT}"
echo "Resource Group: ${RESOURCE_GROUP}"
echo "Location: ${LOCATION}"
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

# Create resource group if it doesn't exist
echo "📦 Creating resource group..."
az group create \
    --name $RESOURCE_GROUP \
    --location $LOCATION \
    --output none

# Create Container Registry
echo "🐳 Creating Azure Container Registry..."
az acr create \
    --resource-group $RESOURCE_GROUP \
    --name $ACR_NAME \
    --sku Basic \
    --location $LOCATION \
    --admin-enabled true \
    --output none 2>/dev/null || echo "ACR already exists"

# Login to ACR
echo "🔑 Logging in to ACR..."
az acr login --name $ACR_NAME || true  # Ignore Docker Desktop warnings on WSL

# Build and push backend
echo "🏗️  Building and pushing backend image..."
cd ../..
docker build -t $ACR_NAME.azurecr.io/prism-backend:$BUILD_TAG -f apps/api/Dockerfile .
docker push $ACR_NAME.azurecr.io/prism-backend:$BUILD_TAG

# Get backend FQDN if it exists (for updates)
BACKEND_FQDN=$(az containerapp show \
    --name $BACKEND_APP \
    --resource-group $RESOURCE_GROUP \
    --query properties.configuration.ingress.fqdn -o tsv 2>/dev/null || echo "")

# If backend doesn't exist yet, use a placeholder (will be updated after backend deployment)
if [ -z "$BACKEND_FQDN" ]; then
    BACKEND_FQDN="backend-placeholder"
    echo "⚠️  Backend not yet deployed, will rebuild frontend after backend deployment"
fi

# Build and push frontend
echo "🏗️  Building and pushing frontend image..."
docker build \
    --build-arg VITE_API_URL=https://$BACKEND_FQDN \
    -t $ACR_NAME.azurecr.io/prism-frontend:$BUILD_TAG \
    -f apps/web/Dockerfile \
    apps/web/
docker push $ACR_NAME.azurecr.io/prism-frontend:$BUILD_TAG

# Create Container Apps environment
echo "🌍 Creating Container Apps environment..."
az containerapp env create \
    --name $CONTAINER_ENV \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --output none 2>/dev/null || echo "Environment already exists"

# Get ACR credentials
echo "🔐 Getting ACR credentials..."
ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)

# Deploy backend
echo "🚀 Deploying backend container app..."
az containerapp create \
    --name $BACKEND_APP \
    --resource-group $RESOURCE_GROUP \
    --environment $CONTAINER_ENV \
    --image $ACR_NAME.azurecr.io/prism-backend:$BUILD_TAG \
    --registry-server $ACR_NAME.azurecr.io \
    --registry-username $ACR_USERNAME \
    --registry-password $ACR_PASSWORD \
    --target-port 8000 \
    --ingress external \
    --min-replicas 1 \
    --max-replicas 3 \
    --cpu 1.0 \
    --memory 2.0Gi \
    --secrets \
        openai-key="${AZURE_OPENAI_API_KEY}" \
        search-key="${AZURE_SEARCH_ADMIN_KEY}" \
        auth-password="${AUTH_PASSWORD}" \
    --env-vars \
        AZURE_OPENAI_API_KEY=secretref:openai-key \
        AZURE_OPENAI_ENDPOINT="${AZURE_OPENAI_ENDPOINT}" \
        AZURE_OPENAI_MODEL_NAME="${AZURE_OPENAI_MODEL_NAME}" \
        AZURE_OPENAI_API_VERSION="${AZURE_OPENAI_API_VERSION}" \
        AZURE_OPENAI_CHAT_DEPLOYMENT_NAME="${AZURE_OPENAI_CHAT_DEPLOYMENT_NAME}" \
        AZURE_SEARCH_ENDPOINT="${AZURE_SEARCH_ENDPOINT}" \
        AZURE_SEARCH_ADMIN_KEY=secretref:search-key \
        AZURE_SEARCH_INDEX_NAME="${AZURE_SEARCH_INDEX_NAME}" \
        AUTH_PASSWORD=secretref:auth-password \
    --output none 2>/dev/null || {
        echo "Updating existing backend app..."
        az containerapp update \
            --name $BACKEND_APP \
            --resource-group $RESOURCE_GROUP \
            --image $ACR_NAME.azurecr.io/prism-backend:$BUILD_TAG \
            --revision-suffix "v$(date +%s)" \
            --replace-secrets \
                openai-key="${AZURE_OPENAI_API_KEY}" \
                search-key="${AZURE_SEARCH_ADMIN_KEY}" \
                auth-password="${AUTH_PASSWORD}" \
            --replace-env-vars \
                AZURE_OPENAI_API_KEY=secretref:openai-key \
                AZURE_OPENAI_ENDPOINT="${AZURE_OPENAI_ENDPOINT}" \
                AZURE_OPENAI_MODEL_NAME="${AZURE_OPENAI_MODEL_NAME}" \
                AZURE_OPENAI_API_VERSION="${AZURE_OPENAI_API_VERSION}" \
                AZURE_OPENAI_CHAT_DEPLOYMENT_NAME="${AZURE_OPENAI_CHAT_DEPLOYMENT_NAME}" \
                AZURE_SEARCH_ENDPOINT="${AZURE_SEARCH_ENDPOINT}" \
                AZURE_SEARCH_ADMIN_KEY=secretref:search-key \
                AZURE_SEARCH_INDEX_NAME="${AZURE_SEARCH_INDEX_NAME}" \
                AUTH_PASSWORD=secretref:auth-password \
            --output none
    }

# Get backend FQDN (refresh after deployment)
echo "🔍 Getting backend URL..."
BACKEND_FQDN_NEW=$(az containerapp show \
    --name $BACKEND_APP \
    --resource-group $RESOURCE_GROUP \
    --query properties.configuration.ingress.fqdn -o tsv)

echo "Backend URL: https://$BACKEND_FQDN_NEW"

# If this is first deployment, rebuild frontend with correct backend URL
if [ "$BACKEND_FQDN" == "backend-placeholder" ]; then
    echo "🏗️  Rebuilding frontend with correct backend URL..."
    docker build \
        --build-arg VITE_API_URL=https://$BACKEND_FQDN_NEW \
        -t $ACR_NAME.azurecr.io/prism-frontend:$BUILD_TAG-rebuild \
        -f apps/web/Dockerfile \
        apps/web/
    docker push $ACR_NAME.azurecr.io/prism-frontend:$BUILD_TAG-rebuild
    BUILD_TAG="${BUILD_TAG}-rebuild"  # Update tag for frontend deployment
    BACKEND_FQDN=$BACKEND_FQDN_NEW
else
    BACKEND_FQDN=$BACKEND_FQDN_NEW
fi

# Deploy frontend
echo "🚀 Deploying frontend container app..."
az containerapp create \
    --name $FRONTEND_APP \
    --resource-group $RESOURCE_GROUP \
    --environment $CONTAINER_ENV \
    --image $ACR_NAME.azurecr.io/prism-frontend:$BUILD_TAG \
    --registry-server $ACR_NAME.azurecr.io \
    --registry-username $ACR_USERNAME \
    --registry-password $ACR_PASSWORD \
    --target-port 80 \
    --ingress external \
    --min-replicas 1 \
    --max-replicas 5 \
    --cpu 0.5 \
    --memory 1.0Gi \
    --output none 2>/dev/null || {
        echo "Updating existing frontend app..."
        az containerapp update \
            --name $FRONTEND_APP \
            --resource-group $RESOURCE_GROUP \
            --image $ACR_NAME.azurecr.io/prism-frontend:$BUILD_TAG \
            --revision-suffix "v$(date +%s)" \
            --output none
    }

# Get frontend URL
echo "🔍 Getting frontend URL..."
FRONTEND_URL=$(az containerapp show \
    --name $FRONTEND_APP \
    --resource-group $RESOURCE_GROUP \
    --query properties.configuration.ingress.fqdn -o tsv)

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Frontend URL: https://$FRONTEND_URL"
echo "🔧 Backend URL: https://$BACKEND_FQDN"
echo ""
echo "📊 View logs:"
echo "  Backend:  az containerapp logs show --name $BACKEND_APP --resource-group $RESOURCE_GROUP --follow"
echo "  Frontend: az containerapp logs show --name $FRONTEND_APP --resource-group $RESOURCE_GROUP --follow"
echo ""
echo "🔐 Login with password from .env: AUTH_PASSWORD"
echo ""
