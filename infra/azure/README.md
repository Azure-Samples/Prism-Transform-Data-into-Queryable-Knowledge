# Azure Infrastructure Deployment Guide

This guide covers deploying Prism to Azure, including the required Azure AI Search service.

## Prerequisites

1. Azure CLI installed and authenticated (`az login`)
2. Azure subscription with permissions to create resources
3. Docker installed (for Container Apps deployment)

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    rg-prism-{environment}                       │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │        Azure Container Apps Environment                  │   │
│  │                                                          │   │
│  │  ┌──────────────┐         ┌──────────────┐              │   │
│  │  │   Frontend   │  ───▶   │   Backend    │              │   │
│  │  │  (Port 80)   │         │  (Port 8000) │              │   │
│  │  │   nginx      │         │   FastAPI    │              │   │
│  │  └──────────────┘         └──────────────┘              │   │
│  │                                  │                       │   │
│  └──────────────────────────────────│───────────────────────┘   │
│                                     │                           │
│  ┌──────────────────────────────────▼───────────────────────┐   │
│  │              Azure AI Search (Dedicated)                  │   │
│  │                                                           │   │
│  │  - Indexes (per project)                                  │   │
│  │  - Knowledge Sources                                      │   │
│  │  - Knowledge Agents                                       │   │
│  │                                                           │   │
│  └───────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   Azure OpenAI   │
                    │  (External RG)   │
                    └──────────────────┘
```

## Deployment Order

**IMPORTANT:** Deploy in this order to ensure proper isolation:

1. **Deploy Azure AI Search** (creates dedicated search service)
2. **Update .env** with search credentials
3. **Deploy Container Apps** (if deploying to cloud)

## Step 1: Deploy Azure AI Search

This creates a **dedicated** Azure AI Search service for Prism, isolated from other projects.

```bash
cd infra/azure
chmod +x deploy-search.sh
./deploy-search.sh dev      # For development
./deploy-search.sh prod     # For production
```

The script will:
1. Create resource group `rg-prism-{env}`
2. Create Azure AI Search service `srch-prism-{env}-{date}`
3. Output credentials for your `.env` file

### Search Service SKUs

| SKU | Indexes | Storage | Cost | Use Case |
|-----|---------|---------|------|----------|
| free | 3 | 50MB | Free | Testing only |
| basic | 15 | 2GB | ~$70/mo | Development |
| standard | 50 | 25GB | ~$250/mo | Production |

Edit `deploy-search.sh` to change the SKU if needed.

## Step 2: Update .env

After running `deploy-search.sh`, copy the output to your `.env`:

```bash
# Azure AI Search (Prism dedicated)
AZURE_SEARCH_ENDPOINT=https://srch-prism-dev-20251201.search.windows.net
AZURE_SEARCH_ADMIN_KEY=<your-generated-key>
AZURE_SEARCH_API_VERSION=2025-08-01-preview
```

The script also saves credentials to `.env.search.{env}` for reference.

## Step 3: Deploy Container Apps (Optional)

For cloud deployment:

```bash
./deploy.sh dev    # Deploy to dev environment
./deploy.sh prod   # Deploy to production
```

This creates:
- Azure Container Registry
- Container Apps Environment
- Backend container (FastAPI)
- Frontend container (nginx + Vue)

## Resource Naming Convention

| Resource | Name Pattern | Example |
|----------|--------------|---------|
| Resource Group | `rg-prism-{env}` | `rg-prism-dev` |
| Search Service | `srch-prism-{env}-{date}` | `srch-prism-dev-20251201` |
| Container Registry | `acrprism{env}` | `acrprismdev` |
| Container Environment | `env-prism-{env}` | `env-prism-dev` |
| Backend App | `prism-backend-{env}` | `prism-backend-dev` |
| Frontend App | `prism-frontend-{env}` | `prism-frontend-dev` |

## Local Development

For local development with Docker Compose:

1. Run `deploy-search.sh` to create a dedicated search service
2. Update `.env` with the search credentials
3. Run `docker-compose -f infra/docker/docker-compose.yml up -d`

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `deploy-search.sh` | Create dedicated Azure AI Search service |
| `deploy.sh` | Full deployment (ACR + Container Apps) |
| `deploy-frontend-only.sh` | Rebuild and deploy frontend only |
| `sync-storage.sh` | Sync project files to Azure Storage |

## Monitoring

```bash
# View search service status
az search service show \
  --name srch-prism-dev-20251201 \
  --resource-group rg-prism-dev

# View backend logs
az containerapp logs show \
  --name prism-backend-dev \
  --resource-group rg-prism-dev \
  --follow

# View frontend logs
az containerapp logs show \
  --name prism-frontend-dev \
  --resource-group rg-prism-dev \
  --follow
```

## Cleanup

```bash
# Delete search service only
az search service delete \
  --name srch-prism-dev-20251201 \
  --resource-group rg-prism-dev

# Delete entire resource group (removes ALL resources)
az group delete --name rg-prism-dev --yes
```

## Troubleshooting

### Search service creation fails
- Check subscription quota for Azure AI Search
- Try a different region
- Ensure unique service name

### Index creation fails
- Verify `AZURE_SEARCH_ENDPOINT` is correct
- Check `AZURE_SEARCH_ADMIN_KEY` has write permissions
- Ensure API version is `2025-08-01-preview` or later

### Knowledge Agent errors
- Verify Azure OpenAI is deployed and accessible
- Check `AZURE_OPENAI_AGENT_MODEL_NAME` is an exact model name (e.g., `gpt-4.1`)
- Ensure semantic configuration is enabled on the index

### Container Apps not starting
- Check secrets are set correctly
- Verify environment variables in Azure Portal
- Review container logs for Python errors
