# Prism Quick Start Guide

Get Prism running in 5 minutes!

## Prerequisites

- Docker and Docker Compose installed
- `.env` file with Azure credentials

## 1. Configure Environment

Copy `.env.example` to `.env` and fill in your values:

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
AUTH_PASSWORD=your-password
```

## 2. Start the Application

```bash
docker-compose -f infra/docker/docker-compose.yml --env-file .env up -d
```

Docker will build and start both frontend and backend services.

## 3. Access the Application

- **Web UI**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs

## Using Prism

### Create a Project

1. Click "Projects" in the navigation
2. Click "New Project"
3. Enter a project name
4. Project folder is created automatically

### Upload Documents

1. Open your project
2. Drag and drop files into the upload area
3. Supports PDF, Excel (.xlsx), and Email (.msg) files

### Process Documents (Pipeline)

Run the processing pipeline step by step:

1. **Process** - Extract content from documents
2. **Deduplicate** - Remove duplicate content
3. **Chunk** - Split into searchable chunks
4. **Embed** - Generate vector embeddings
5. **Index Create** - Create Azure AI Search index
6. **Index Upload** - Upload to search index
7. **Source Create** - Create knowledge source
8. **Agent Create** - Create knowledge agent

Click "Run" on each step, or use "Run All" to execute the full pipeline.

### Configure Workflows

1. Click "Configure Workflow" on your project
2. Add sections (groups of related questions)
3. Add questions to each section
4. Set templates and instructions for each section

### Query Documents

1. Click "Query" in the navigation
2. Select your project
3. Type your question
4. Get AI-generated answers with citations

### Run Workflows

1. Click "Workflows" in the navigation
2. Select a section to run
3. Watch progress in real-time
4. View results when complete

## Stop the Application

```bash
# Press Ctrl+C, then:
docker-compose -f infra/docker/docker-compose.yml down
```

## Troubleshooting

### Containers won't start?
```bash
# Check ports
lsof -i :8000  # Backend
lsof -i :3000  # Frontend

# View logs
docker-compose -f infra/docker/docker-compose.yml logs backend
docker-compose -f infra/docker/docker-compose.yml logs frontend
```

### Backend not responding?
```bash
curl http://localhost:8000/health
# Should return: {"status": "healthy"}
```

### Need to rebuild?
```bash
docker-compose -f infra/docker/docker-compose.yml --env-file .env up -d --build
```

## Next Steps

- Read [USER_GUIDE.md](USER_GUIDE.md) for detailed usage instructions
- See [infra/azure/README.md](../infra/azure/README.md) for deployment
- Check [CLAUDE.md](../CLAUDE.md) for system architecture
