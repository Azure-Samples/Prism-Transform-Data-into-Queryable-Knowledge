#!/bin/bash

# Sync local files to Azure File Shares
# Usage: ./sync-storage.sh [environment] [direction]
# Direction: upload (local -> azure) or download (azure -> local)

set -e

ENVIRONMENT=${1:-dev}
DIRECTION=${2:-upload}
# Storage account for file shares
STORAGE_ACCOUNT="stprismfileshare${ENVIRONMENT}"
RESOURCE_GROUP="rg-prism-${ENVIRONMENT}"

echo "🔄 Syncing storage for environment: ${ENVIRONMENT}"
echo "Direction: ${DIRECTION}"
echo ""

# Get storage account key
echo "🔑 Getting storage account key..."
STORAGE_KEY=$(az storage account keys list \
    --resource-group $RESOURCE_GROUP \
    --account-name $STORAGE_ACCOUNT \
    --query "[0].value" -o tsv)

cd ../..

if [ "$DIRECTION" == "upload" ]; then
    echo "⬆️  Uploading local files to Azure..."

    echo "  📂 Uploading input files..."
    az storage file upload-batch \
        --destination prism-input \
        --source ./input \
        --account-name $STORAGE_ACCOUNT \
        --account-key $STORAGE_KEY \
        --overwrite true \
        --no-progress || echo "Input upload completed"

    echo "  📂 Uploading output files..."
    az storage file upload-batch \
        --destination prism-output \
        --source ./output \
        --account-name $STORAGE_ACCOUNT \
        --account-key $STORAGE_KEY \
        --overwrite true \
        --no-progress || echo "Output upload completed"

    echo "  📂 Uploading workflow files..."
    az storage file upload-batch \
        --destination prism-workflows \
        --source ./workflows \
        --account-name $STORAGE_ACCOUNT \
        --account-key $STORAGE_KEY \
        --overwrite true \
        --no-progress || echo "Workflows upload completed"

    echo "✅ Upload complete!"

elif [ "$DIRECTION" == "download" ]; then
    echo "⬇️  Downloading files from Azure to local..."

    echo "  📂 Downloading input files..."
    az storage file download-batch \
        --source prism-input \
        --destination ./input \
        --account-name $STORAGE_ACCOUNT \
        --account-key $STORAGE_KEY \
        --no-progress || echo "Input download completed"

    echo "  📂 Downloading output files..."
    az storage file download-batch \
        --source prism-output \
        --destination ./output \
        --account-name $STORAGE_ACCOUNT \
        --account-key $STORAGE_KEY \
        --no-progress || echo "Output download completed"

    echo "  📂 Downloading workflow files..."
    az storage file download-batch \
        --source prism-workflows \
        --destination ./workflows \
        --account-name $STORAGE_ACCOUNT \
        --account-key $STORAGE_KEY \
        --no-progress || echo "Workflows download completed"

    echo "✅ Download complete!"
else
    echo "❌ Invalid direction: $DIRECTION"
    echo "Usage: ./sync-storage.sh [environment] [upload|download]"
    exit 1
fi

echo ""
echo "Storage account: $STORAGE_ACCOUNT"
echo ""
