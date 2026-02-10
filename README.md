<!--
---
name: PrismRAG - Transform Documents into Queryable Knowledge
description: Document intelligence solution accelerator with hybrid extraction agents, Azure AI Search Agentic Retrieval, and structured Q&A workflows.
languages:
- python
- typescript
- bicep
- azdeveloper
products:
- azure-openai
- azure-cognitive-search
- azure-container-apps
- azure
page_type: sample
urlFragment: prism-document-intelligence
---
-->

# PrismRAG - Transform Documents into Queryable Knowledge

A document intelligence solution accelerator built on Azure AI. Extracts structured answers from document collections using AI agents and proves those answers are grounded in actual source material.

[![Open in GitHub Codespaces](https://img.shields.io/static/v1?style=for-the-badge&label=GitHub+Codespaces&message=Open&color=brightgreen&logo=github)](https://codespaces.new/Azure-Samples/Prism---Transform-Data-into-Queryable-Knowledge?devcontainer_path=.devcontainer%2Fdevcontainer.json)
[![Open in Dev Containers](https://img.shields.io/static/v1?style=for-the-badge&label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/Azure-Samples/Prism---Transform-Data-into-Queryable-Knowledge)

https://github.com/user-attachments/assets/f0a4770c-6efd-4935-afda-c3c19da93813

## Important Security Notice

This template is built to showcase Azure AI services. We strongly advise against using this code in production without implementing additional security features. See [productionizing guide](docs/productionizing.md).

![Prism Extraction Pipeline](docs/images/thumbnail.png)

## What Makes Prism Different

| Challenge | Prism's Solution |
|-----------|------------------|
| **Inconsistent PDF extraction** | Azure Document Intelligence extracts PDFs with native markdown output, HTML tables, and layout detection. No local dependencies. |
| **Poor table extraction** | Document Intelligence preserves table structure with merged cells/rowspan/colspan. openpyxl extracts Excel with formulas and formatting. |
| **Lost document structure** | Structure-aware chunking respects markdown hierarchy (##, ###). Extracts section titles as metadata. |
| **Hallucinated answers** | Agentic retrieval with strict grounding instructions. Always cites sources. Distinguishes "not found" vs "explicitly excluded." |
| **Manual Q&A workflows** | Define question templates per project. Run workflows against your knowledge base. Export results to CSV. |

## Features

### Document Extraction

Documents go through extraction using Azure services and [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) for enhancement.

**PDF Processing**
- **Azure Document Intelligence**: `prebuilt-layout` model with native markdown output, HTML tables, figure tags, and selection marks
- **Custom instructions**: Project-specific extraction prompts via `config.json`

**Excel Processing**
- **openpyxl**: Extracts all worksheets (including hidden), formulas, merged cells
- **Excel_Enhancement agent**: Restructures raw data into search-optimized markdown, preserving item numbers, part codes, specifications

**Email Processing**
- **python-oxmsg**: MIT-licensed .msg file parsing with metadata and body extraction
- **Email_Enhancement agent**: Classifies email purpose and urgency, extracts requirements and action items, identifies deadlines, generates summaries

### RAG Pipeline

```
Upload → Extract → Deduplicate → Chunk → Embed → Index → Query
```

| Stage | What It Does |
|-------|--------------|
| **Extract** | Azure Document Intelligence + AI agent extraction to structured markdown |
| **Deduplicate** | SHA256 hashing removes duplicate content |
| **Chunk** | Document-aware recursive chunking (1000 tokens, 200 overlap) |
| **Embed** | text-embedding-3-large (1024 dimensions, batch processing) |
| **Index** | Azure AI Search with hybrid search + semantic ranking |
| **Query** | Agentic retrieval with Knowledge Source + Knowledge Base |

### Chunking

Before embedding, documents go through document-aware recursive chunking:
- PDFs split on page boundaries, Excel on sheet markers, emails on metadata/body/attachment sections
- Chunks target 1000 tokens with 200-token overlap, using [tiktoken](https://github.com/openai/tiktoken) for accurate counting
- Preserves markdown header hierarchy (H1-H4) as metadata, merges small sections with neighbors
- Table-aware regex avoids breaking markdown tables mid-row
- Each chunk enriched with context prefix (document name, section hierarchy, location) to improve embedding quality

### Azure AI Search Agentic Retrieval

PrismRAG uses [Azure AI Search Agentic Retrieval](https://learn.microsoft.com/azure/search/agentic-retrieval-overview) for intelligent document retrieval.

The search index uses hybrid search: HNSW vectors with cosine distance, full-text search, and semantic ranking (required for agentic retrieval). On top of the index sits a two-layer architecture:

1. **Knowledge Source** - wraps the search index with properties for agentic retrieval
2. **Knowledge Base** - orchestrates the multi-query pipeline, connects to the LLM

When you submit a query with conversation history, agentic retrieval:
- Uses the LLM (gpt-4o, gpt-4.1, or gpt-5) to analyze context and break the query into focused subqueries
- Executes all subqueries in parallel against the knowledge source
- Applies semantic reranking to filter results
- Returns grounding data, source references, and execution details

Your application then uses this grounding data to generate the final answer. PrismRAG adds custom retry logic: if the original query returns nothing, it tries a simplified version (removing acronyms), then an expanded version (adding synonyms).

### Workflow System

Define structured Q&A templates for systematic document analysis:

```json
{
  "sections": [
    {
      "name": "Technical Specifications",
      "template": "Answer based on technical documents. Provide specific values with units.",
      "questions": [
        { "question": "What is the rated voltage?", "instructions": "Check electrical specs" },
        { "question": "Operating temperature range?", "instructions": "Check environmental specs" }
      ]
    }
  ]
}
```

- Run workflows against your knowledge base
- Track completion percentage per section
- Export results to CSV
- Edit and comment on answers
- **Evaluation**: Assess answer quality with [Azure AI Evaluation SDK](https://learn.microsoft.com/azure/ai-studio/how-to/develop/evaluate-sdk) (relevance, coherence, fluency, groundedness)

## Architecture

See [Architecture Documentation](docs/architecture.md) for detailed system design.

## Tech Stack

### Azure AI Services

| Service | Purpose |
|---------|---------|
| [Azure AI Foundry](https://azure.microsoft.com/products/ai-foundry) | GPT-4.1 (chat, evaluation), GPT-5-chat (extraction agents, workflows), text-embedding-3-large (1024 dimensions) |
| [Azure AI Search Agentic Retrieval](https://learn.microsoft.com/azure/search/agentic-retrieval-overview) | Knowledge Source + Knowledge Base for multi-query retrieval pipeline |
| [Azure AI Evaluation SDK](https://learn.microsoft.com/azure/ai-studio/how-to/develop/evaluate-sdk) | Answer quality scoring (relevance, coherence, fluency, groundedness) |
| **Azure Blob Storage** | Document and project data storage |
| **Container Apps** | Serverless hosting for backend/frontend |

### Agent Frameworks

| Framework | Purpose |
|-----------|---------|
| [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) | Orchestrates extraction agents (Vision_Validator, Excel_Enhancement, Email_Enhancement) and workflow agents |

### Azure Services (Extraction)

| Service | Purpose |
|---------|---------|
| [Azure Document Intelligence](https://learn.microsoft.com/azure/ai-services/document-intelligence/) | PDF extraction with `prebuilt-layout` model (markdown, tables, figures) |

### Open Source Libraries

| Library | License | Purpose |
|---------|---------|---------|
| [openpyxl](https://openpyxl.readthedocs.io/) | MIT | Excel extraction with formula support |
| [python-oxmsg](https://github.com/scanny/python-oxmsg) | MIT | Outlook .msg email parsing |
| [tiktoken](https://github.com/openai/tiktoken) | MIT | Token counting for accurate chunk sizing |
| [LangChain text splitters](https://api.python.langchain.com/en/latest/text_splitters/character/langchain_text_splitters.character.RecursiveCharacterTextSplitter.html) | MIT | Structure-aware recursive chunking |

### Application

| Component | Technology |
|-----------|------------|
| **Backend** | FastAPI (Python 3.11) |
| **Frontend** | Vue 3 + Vite + TailwindCSS + Pinia |
| **Infrastructure** | Bicep + Azure Developer CLI |

## Getting Started

### Prerequisites

- Azure subscription with permissions to create resources
- [Azure Developer CLI](https://aka.ms/azd-install)
- [Docker](https://docs.docker.com/get-docker/)

### Deploy

```bash
# Clone and deploy
git clone https://github.com/Azure-Samples/Prism---Transform-Data-into-Queryable-Knowledge.git
cd Prism---Transform-Data-into-Queryable-Knowledge

azd auth login
azd up
```

**What gets deployed:**
- AI Foundry with GPT-4.1, text-embedding-3-large
- Azure Document Intelligence for PDF extraction
- Azure AI Search with semantic ranking enabled
- Azure Blob Storage for project data
- Container Apps with system-assigned managed identity (backend + frontend)
- RBAC role assignments (Storage Blob Data Contributor, Cognitive Services OpenAI User)
- Container Registry, Log Analytics, Application Insights

> **⚠️ Manual step required:** `azd up` does **not** deploy the `gpt-5-chat` model. If you want to use it for workflows, deploy it manually through the [Azure Portal](https://portal.azure.com) → your AI Foundry resource → Model deployments. Otherwise, update `AZURE_OPENAI_WORKFLOW_DEPLOYMENT_NAME` in your `.env` to `gpt-4.1`.

**Get the auth password:**
```bash
az containerapp secret show --name prism-backend --resource-group <your-rg> --secret-name auth-password --query value -o tsv
```

### Run Locally (after deploying to Azure)

After running `azd up`, generate a local `.env` file from your deployed Container App:

```bash
# Set your resource group
RG=<your-rg>

# Get environment variables and secrets
az containerapp show --name prism-backend --resource-group $RG \
  --query "properties.template.containers[0].env[?value!=null].{name:name, value:value}" \
  -o tsv | awk '{print $1"="$2}' > .env

# Append secrets
echo "AZURE_OPENAI_API_KEY=$(az containerapp secret show --name prism-backend --resource-group $RG --secret-name ai-services-key --query value -o tsv)" >> .env
echo "AZURE_SEARCH_ADMIN_KEY=$(az containerapp secret show --name prism-backend --resource-group $RG --secret-name search-admin-key --query value -o tsv)" >> .env
echo "AUTH_PASSWORD=$(az containerapp secret show --name prism-backend --resource-group $RG --secret-name auth-password --query value -o tsv)" >> .env
```

Then run locally:
```bash
docker-compose -f infra/docker/docker-compose.yml --env-file .env up -d
```

Access at http://localhost:3000

## Project Structure

```
prism/
├── apps/
│   ├── api/                      # FastAPI backend
│   │   └── app/
│   │       ├── api/              # REST endpoints
│   │       └── services/         # Pipeline, workflow, storage services
│   └── web/                      # Vue 3 frontend
│       └── src/views/            # Dashboard, Query, Workflows, Results
├── scripts/
│   ├── extraction/               # Document extractors
│   │   ├── pdf_extraction_di.py        # Azure Document Intelligence
│   │   ├── excel_extraction_agents.py  # openpyxl + AI
│   │   └── email_extraction_agents.py  # python-oxmsg + AI
│   ├── rag/                      # RAG pipeline
│   │   ├── deduplicate_documents.py
│   │   ├── chunk_documents.py    # Structure-aware chunking
│   │   └── generate_embeddings.py
│   ├── search_index/             # Azure AI Search
│   │   ├── create_search_index.py
│   │   ├── create_knowledge_source.py
│   │   └── create_knowledge_agent.py
│   └── evaluation/               # Answer quality evaluation
│       └── evaluate_results.py
├── workflows/
│   └── workflow_agent.py         # Q&A workflow execution
└── infra/
    ├── bicep/                    # Azure infrastructure
    └── docker/                   # Local development (includes Azurite)
```

## Storage & Authentication

All project data is stored in Azure Blob Storage:

- **Production**: Azure Blob Storage with managed identity authentication (no keys required)
- **Local Development**: Azurite (Azure Storage emulator, included in docker-compose)

**Authentication**: Uses `DefaultAzureCredential` from `azure-identity`, which automatically:
- In Container Apps: Uses system-assigned managed identity
- In local development: Uses Azure CLI credentials (`az login`)

```
Container: prism-projects
└── {project-name}/
    ├── documents/            # Uploaded files
    ├── output/               # Processed results
    │   ├── extraction_results/*.md
    │   ├── chunked_documents/*.json
    │   ├── embedded_documents/*.json
    │   └── results.json      # Workflow answers + evaluations
    ├── config.json           # Extraction instructions
    └── workflow_config.json  # Q&A templates
```

Browse local storage with [Azure Storage Explorer](https://azure.microsoft.com/features/storage-explorer/) connected to `http://localhost:10000`.

## Cost Estimation

| Service | SKU | Pricing |
|---------|-----|---------|
| Azure Container Apps | Consumption | [Pricing](https://azure.microsoft.com/pricing/details/container-apps/) |
| Azure OpenAI | Standard | [Pricing](https://azure.microsoft.com/pricing/details/cognitive-services/openai-service/) |
| Azure AI Search | Basic | [Pricing](https://azure.microsoft.com/pricing/details/search/) |

> **Note**: Azure Document Intelligence pricing is ~$1.50/1000 pages. See [Azure pricing](https://azure.microsoft.com/pricing/details/ai-document-intelligence/).

## Clean Up

```bash
azd down
```

## Documentation

- [Quick Start](docs/QUICKSTART.md) - Get running in 5 minutes
- [User Guide](docs/USER_GUIDE.md) - Complete usage instructions
- [Architecture](docs/architecture.md) - System design details
- [Data Ingestion](docs/data_ingestion.md) - Supported formats and pipeline
- [Troubleshooting](docs/troubleshooting.md) - Common issues
- [Productionizing](docs/productionizing.md) - Production readiness
- [Local Development](docs/localdev.md) - Development setup

## Resources

- [Azure AI Foundry](https://azure.microsoft.com/products/ai-foundry)
- [Azure AI Search Agentic Retrieval](https://learn.microsoft.com/azure/search/agentic-retrieval-overview)
- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
- [Azure AI Evaluation SDK](https://learn.microsoft.com/azure/ai-studio/how-to/develop/evaluate-sdk)
- [Azure Document Intelligence](https://learn.microsoft.com/azure/ai-services/document-intelligence/)

## Getting Help

- [GitHub Issues](../../issues)

## License

MIT License - see [LICENSE](LICENSE)

All third-party dependencies use permissive licenses (MIT, BSD, Apache 2.0). See [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) for details.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft trademarks or logos is subject to and must follow [Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).
