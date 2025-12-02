# Prism

Transform unstructured documents into queryable knowledge. Upload files, extract content, and get structured answers.

## What It Does

```
[Upload Files] → [Process] → [Index] → [Query]
```

1. **Upload** any documents (PDFs, Excel, emails, images)
2. **Process** extracts content using AI vision and text analysis
3. **Index** creates a searchable knowledge base
4. **Query** ask questions, get structured answers

## Features

- **Multi-format support** - PDFs, Excel, Word, emails (.msg), images
- **AI-powered extraction** - Vision AI for diagrams, text extraction for documents
- **Semantic search** - Azure AI Search with vector + hybrid search
- **Structured workflows** - Define sections and questions, get organized answers
- **Self-service UI** - Full pipeline accessible through web interface

## Tech Stack

**Backend:**
- Python 3.11
- FastAPI
- Azure OpenAI GPT-4 (vision & chat)
- Azure AI Search (vector + hybrid)

**Frontend:**
- Node.js 20
- Vue 3 + Vite
- TailwindCSS
- Pinia (state management)

**Infrastructure:**
- Docker + Docker Compose
- Azure Container Apps ready

## Prerequisites

### Required Software
- Docker & Docker Compose (recommended for running the app)
- For local development only:
  - Python 3.11+
  - Node.js 20+

### Azure Resources

You need two Azure services. Basic/Free tiers work fine for development.

**1. Azure OpenAI Service**
- Create an Azure OpenAI resource in [Azure Portal](https://portal.azure.com)
- Deploy a GPT-4 model (any variant: gpt-4, gpt-4o, gpt-4-turbo)
- Note your endpoint, API key, and deployment name

**2. Azure AI Search**
- Create an Azure AI Search resource (Basic tier is sufficient)
- Note your endpoint and admin key

## Quick Start (Docker - Recommended)

### 1. Configure

Create `.env` file:
```bash
# Azure OpenAI
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_MODEL_NAME=gpt-4
AZURE_OPENAI_API_VERSION=2025-01-01-preview
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt-4

# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_ADMIN_KEY=your-key

# Authentication
AUTH_PASSWORD=your-secure-password
```

### 2. Run

```bash
docker-compose -f infra/docker/docker-compose.yml --env-file .env up -d
```

Access:
- **App**: http://localhost:3000
- **API**: http://localhost:8000/docs

### 3. Use

1. Login with your password
2. Create a new project
3. Upload documents
4. Click "Process" to extract content
5. Click "Create Index" to make searchable
6. Query your knowledge base

## Local Development (Optional)

If you need to run without Docker for debugging or development:

**Backend:**
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r apps/api/requirements-api.txt

# Run API server
uvicorn apps.api.app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd apps/web
npm install
npm run dev
```

## CLI Commands

For development and scripting, you can run pipeline steps directly:

```bash
# Process documents for a project
python main.py process --project myproject

# RAG pipeline steps
python main.py deduplicate --project myproject
python main.py chunk --project myproject
python main.py embed --project myproject

# Index operations
python main.py index create --project myproject
python main.py index upload --project myproject
```

## Testing

Tests use pytest:

```bash
# Install test dependencies (included in requirements.txt)
pip install pytest pytest-asyncio

# Run all tests
pytest

# Run specific test file
pytest tests/test_workflow_service.py

# Run with verbose output
pytest -v
```

## Project Structure

```
prism/
├── apps/
│   ├── api/              # FastAPI backend
│   └── web/              # Vue frontend
├── projects/             # User projects (created via UI)
│   └── {project_name}/
│       ├── documents/    # Uploaded files
│       ├── output/       # Processed results
│       ├── config.json   # Extraction settings
│       └── workflow_config.json
├── scripts/
│   ├── extraction/       # Document extractors
│   ├── rag/              # Chunking & embedding
│   └── search_index/     # Index management
├── infra/
│   ├── azure/            # Deployment scripts
│   └── docker/           # Docker configuration
└── tests/                # Test suite
```

## Configuration Files

Project configuration is managed through the web UI, not by editing files directly.

- **`config.json`** - Extraction settings (created when you configure a project in the UI)
- **`workflow_config.json`** - Sections and questions for structured querying (created via Workflow tab in UI)

To configure a project:
1. Open the project in the web UI
2. Go to Settings to configure extraction instructions
3. Go to Workflow to define sections and questions

## Deployment

### Azure Container Apps

```bash
cd infra/azure
./deploy.sh dev    # Deploy to dev
./deploy.sh prod   # Deploy to production
```

## API

Key endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/projects` | GET/POST | List/create projects |
| `/api/projects/{name}/files` | POST | Upload files |
| `/api/projects/{name}/process` | POST | Run extraction |
| `/api/projects/{name}/index` | POST | Create search index |
| `/api/projects/{name}/agent` | POST | Create knowledge agent |
| `/api/query` | POST | Query knowledge base |

Full API docs at `/docs` when running.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft
trademarks or logos is subject to and must follow
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
