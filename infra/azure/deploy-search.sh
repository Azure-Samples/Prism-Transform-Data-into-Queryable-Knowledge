#!/bin/bash

# Azure AI Search Deployment Script for Prism
# This creates a DEDICATED Azure AI Search service for Prism
#
# IMPORTANT: This creates an isolated search service to avoid conflicts
# with other projects. Each Prism deployment should have its own search service.
#
# Usage: ./deploy-search.sh [environment]
# Environment: dev, staging, prod (default: dev)

set -e  # Exit on error

# Configuration
ENVIRONMENT=${1:-dev}
RESOURCE_GROUP="rg-prism-${ENVIRONMENT}"
LOCATION="eastus"
SEARCH_SERVICE_NAME="srch-prism-${ENVIRONMENT}-$(date +%Y%m%d)"
SEARCH_SKU="basic"  # Options: free, basic, standard, standard2, standard3

echo "============================================================"
echo "  Prism Azure AI Search Deployment"
echo "============================================================"
echo ""
echo "Environment:     ${ENVIRONMENT}"
echo "Resource Group:  ${RESOURCE_GROUP}"
echo "Location:        ${LOCATION}"
echo "Search Service:  ${SEARCH_SERVICE_NAME}"
echo "SKU:             ${SEARCH_SKU}"
echo ""
echo "============================================================"
echo ""

# Check if logged in to Azure
echo "Checking Azure CLI authentication..."
az account show > /dev/null 2>&1 || {
    echo "ERROR: Not logged in to Azure. Run 'az login' first."
    exit 1
}

SUBSCRIPTION=$(az account show --query name -o tsv)
echo "Subscription: ${SUBSCRIPTION}"
echo ""

# Confirm before proceeding
read -p "Create Azure AI Search service in ${RESOURCE_GROUP}? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Cancelled."
    exit 0
fi

echo ""

# Create resource group if it doesn't exist
echo "[1/4] Creating resource group..."
az group create \
    --name $RESOURCE_GROUP \
    --location $LOCATION \
    --output none
echo "      Resource group '${RESOURCE_GROUP}' ready"

# Create Azure AI Search service
echo "[2/4] Creating Azure AI Search service (this may take 2-5 minutes)..."
az search service create \
    --name $SEARCH_SERVICE_NAME \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --sku $SEARCH_SKU \
    --partition-count 1 \
    --replica-count 1 \
    --output none

echo "      Search service '${SEARCH_SERVICE_NAME}' created"

# Get search service details
echo "[3/4] Retrieving service credentials..."
SEARCH_ENDPOINT="https://${SEARCH_SERVICE_NAME}.search.windows.net"
SEARCH_ADMIN_KEY=$(az search admin-key show \
    --service-name $SEARCH_SERVICE_NAME \
    --resource-group $RESOURCE_GROUP \
    --query primaryKey -o tsv)

echo "      Credentials retrieved"

# Output configuration
echo "[4/4] Generating configuration..."
echo ""
echo "============================================================"
echo "  DEPLOYMENT COMPLETE"
echo "============================================================"
echo ""
echo "Add these to your .env file:"
echo ""
echo "# Azure AI Search (Prism dedicated - ${ENVIRONMENT})"
echo "AZURE_SEARCH_ENDPOINT=${SEARCH_ENDPOINT}"
echo "AZURE_SEARCH_ADMIN_KEY=${SEARCH_ADMIN_KEY}"
echo "AZURE_SEARCH_API_VERSION=2025-08-01-preview"
echo ""
echo "============================================================"
echo ""
echo "Resource Group:  ${RESOURCE_GROUP}"
echo "Search Service:  ${SEARCH_SERVICE_NAME}"
echo "Endpoint:        ${SEARCH_ENDPOINT}"
echo ""
echo "Next steps:"
echo "  1. Update your .env file with the values above"
echo "  2. Restart the application to use the new search service"
echo "  3. Use the UI Pipeline view to create index and upload documents"
echo ""
echo "To delete this search service:"
echo "  az search service delete --name ${SEARCH_SERVICE_NAME} --resource-group ${RESOURCE_GROUP}"
echo ""
echo "To delete the entire resource group:"
echo "  az group delete --name ${RESOURCE_GROUP} --yes"
echo ""

# Optionally save to file
ENV_FILE="../../.env.search.${ENVIRONMENT}"
cat > "$ENV_FILE" << EOF
# Azure AI Search (Prism dedicated - ${ENVIRONMENT})
# Generated: $(date)
# Resource Group: ${RESOURCE_GROUP}
# Service: ${SEARCH_SERVICE_NAME}

AZURE_SEARCH_ENDPOINT=${SEARCH_ENDPOINT}
AZURE_SEARCH_ADMIN_KEY=${SEARCH_ADMIN_KEY}
AZURE_SEARCH_API_VERSION=2025-08-01-preview
EOF

echo "Configuration saved to: ${ENV_FILE}"
echo ""
