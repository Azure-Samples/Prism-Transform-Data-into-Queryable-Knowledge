# Local Development

This guide covers setting up a local development environment for Prism.

## Prerequisites

- Docker (required)
- Azure subscription with OpenAI and AI Search resources

## Quick Start with Docker

```bash
# Ensure .env file is configured with Azure credentials
docker-compose -f infra/docker/docker-compose.yml --env-file .env up -d
```

Access:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Azurite Blob Storage: http://localhost:10000

## Storage

Local development uses **Azurite** (Azure Storage emulator) for blob storage. This is automatically started by docker-compose.

All project data (documents, extraction results, workflow answers) is stored in Azurite at:
- Container: `prism-projects`
- Connection string: `DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=...;BlobEndpoint=http://azurite:10000/devstoreaccount1;`

You can browse Azurite data using [Azure Storage Explorer](https://azure.microsoft.com/features/storage-explorer/) connected to `http://localhost:10000`.

## Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
# Azure OpenAI
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-resource.cognitiveservices.azure.com
AZURE_OPENAI_MODEL_NAME=gpt-4.1
AZURE_OPENAI_API_VERSION=2025-01-01-preview
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt-4.1
AZURE_OPENAI_WORKFLOW_DEPLOYMENT_NAME=gpt-5-chat  # Optional: separate model for workflows
AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME=text-embedding-3-large

# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_ADMIN_KEY=your-key

# Authentication
AUTH_PASSWORD=dev-password

# Optional: Debug logging
PRISM_LOG_LEVEL=DEBUG
```

## IDE Setup

### VS Code

Recommended extensions:
- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- Vue - Official (Vue.volar)
- Tailwind CSS IntelliSense (bradlc.vscode-tailwindcss)
- ESLint (dbaeumer.vscode-eslint)
- Prettier (esbenp.prettier-vscode)

Workspace settings (`.vscode/settings.json`):
```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  },
  "[vue]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  }
}
```

### PyCharm

1. Open the project folder
2. Configure Python interpreter to use `.venv`
3. Mark `apps/api` as Sources Root
4. Mark `scripts` as Sources Root

## Debugging

### Backend Debugging (VS Code)

Add to `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Backend: FastAPI",
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": ["apps.api.app.main:app", "--reload", "--port", "8000"],
      "envFile": "${workspaceFolder}/.env"
    }
  ]
}
```

### Frontend Debugging

Use browser DevTools or VS Code's built-in debugger with the Vue extension.

### Logging

Enable debug logging:
```bash
export PRISM_LOG_LEVEL=DEBUG
```

Logging configuration is in `scripts/logging_config.py`.

## Testing

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_workflow_service.py

# Run with coverage
pip install pytest-cov
pytest --cov=apps --cov=scripts
```

### Writing Tests

Tests are in the `tests/` directory. Example:

```python
# tests/test_example.py
import pytest
from apps.api.app.services.project_service import ProjectService

@pytest.fixture
def project_service():
    return ProjectService()

def test_create_project(project_service):
    result = project_service.create("test-project")
    assert result.name == "test-project"
```

## Common Tasks

### Adding a New API Endpoint

1. Create route in `apps/api/app/api/`
2. Add service logic in `apps/api/app/services/`
3. Register route in `apps/api/app/main.py`
4. Add tests in `tests/`

### Adding a New Extractor

1. Create extractor in `scripts/extraction/`
2. Follow pattern of existing extractors
3. Register in pipeline service
4. Add tests

### Modifying the Frontend

1. Components are in `apps/web/src/components/`
2. Views (pages) are in `apps/web/src/views/`
3. API client is in `apps/web/src/services/`
4. State management uses Pinia stores

## Hot Reloading

Both backend and frontend support hot reloading:

- **Backend**: `uvicorn --reload` watches Python files
- **Frontend**: Vite provides HMR (Hot Module Replacement)

## Troubleshooting Development Issues

### Import Errors

Ensure you're using the virtual environment:
```bash
which python  # Should show .venv/bin/python
```

### CORS Issues

The backend includes CORS middleware. If you see CORS errors:
1. Check frontend is hitting the right backend URL
2. Verify CORS origins in `apps/api/app/main.py`

### Hot Reload Not Working

- Backend: Ensure `--reload` flag is set
- Frontend: Check Vite is running, not a production build

### Azure Connection Issues

Test connectivity:
```bash
# Test OpenAI
curl -H "api-key: $AZURE_OPENAI_API_KEY" "$AZURE_OPENAI_ENDPOINT/openai/models?api-version=2023-05-15"

# Test Search
curl -H "api-key: $AZURE_SEARCH_ADMIN_KEY" "$AZURE_SEARCH_ENDPOINT/indexes?api-version=2023-11-01"
```
