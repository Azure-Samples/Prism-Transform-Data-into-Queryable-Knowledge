# Customization

This guide covers how to customize and extend Prism for your specific needs.

## Project Configuration

### Extraction Instructions

Customize how documents are extracted per project in `config.json`:

```json
{
  "extraction_instructions": "Focus on technical specifications. Extract all measurements, tolerances, and standards references. Pay special attention to electrical and mechanical requirements."
}
```

This prompt is included when calling Azure OpenAI for extraction and Vision processing.

### Workflow Configuration

Define structured Q&A workflows in `workflow_config.json`:

```json
{
  "sections": [
    {
      "id": "technical",
      "name": "Technical Specifications",
      "template": "Answer based on technical documents. Provide specific values with units. If not found, state 'Not specified'.",
      "questions": [
        {
          "id": "voltage",
          "question": "What is the rated voltage?",
          "instructions": "Look in electrical specifications section."
        },
        {
          "id": "temperature",
          "question": "What is the operating temperature range?",
          "instructions": "Check environmental specifications."
        }
      ]
    }
  ]
}
```

## Backend Customization

### Adding a New Extractor

1. Create a new extractor in `scripts/extraction/`:

```python
# scripts/extraction/word_extraction.py
from pathlib import Path
from docx import Document

def extract_word(file_path: Path) -> str:
    """Extract text from Word document."""
    doc = Document(file_path)
    content = []

    for para in doc.paragraphs:
        content.append(para.text)

    for table in doc.tables:
        for row in table.rows:
            row_text = [cell.text for cell in row.cells]
            content.append(" | ".join(row_text))

    return "\n\n".join(content)
```

2. Register in the pipeline service:

```python
# apps/api/app/services/pipeline_service.py
from scripts.extraction.word_extraction import extract_word

EXTRACTORS = {
    ".pdf": extract_pdf,
    ".xlsx": extract_excel,
    ".msg": extract_email,
    ".docx": extract_word,  # Add new extractor
}
```

### Adding a New API Endpoint

1. Create route file:

```python
# apps/api/app/api/custom.py
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/custom", tags=["custom"])

@router.get("/status")
async def get_status():
    return {"status": "ok"}

@router.post("/process")
async def custom_process(data: dict):
    # Custom processing logic
    return {"result": "processed"}
```

2. Register in main.py:

```python
# apps/api/app/main.py
from apps.api.app.api import custom

app.include_router(custom.router)
```

### Modifying the RAG Pipeline

Customize chunking in `scripts/rag/chunk_documents.py`:

```python
# Adjust chunk parameters
CHUNK_SIZE = 1000  # tokens
CHUNK_OVERLAP = 100  # tokens

def chunk_document(content: str) -> list[dict]:
    # Custom chunking logic
    pass
```

Customize embedding in `scripts/rag/generate_embeddings.py`:

```python
# Change embedding model
EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIMENSIONS = 3072
```

## Frontend Customization

### Adding a New View

1. Create the view component:

```vue
<!-- apps/web/src/views/CustomView.vue -->
<template>
  <div class="container mx-auto p-4">
    <h1 class="text-2xl font-bold">Custom View</h1>
    <!-- Your content -->
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from '@/services/api'

const data = ref(null)

onMounted(async () => {
  data.value = await api.get('/custom/status')
})
</script>
```

2. Add route:

```javascript
// apps/web/src/router/index.js
{
  path: '/custom',
  name: 'custom',
  component: () => import('@/views/CustomView.vue')
}
```

3. Add navigation link:

```vue
<!-- In your navigation component -->
<router-link to="/custom">Custom</router-link>
```

### Styling

Prism uses TailwindCSS. Customize in `tailwind.config.js`:

```javascript
// apps/web/tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: '#your-color',
        secondary: '#your-color',
      },
      fontFamily: {
        sans: ['Your Font', 'sans-serif'],
      },
    },
  },
}
```

### Adding Components

Create reusable components in `apps/web/src/components/`:

```vue
<!-- apps/web/src/components/CustomCard.vue -->
<template>
  <div class="bg-white rounded-lg shadow p-4">
    <slot></slot>
  </div>
</template>
```

## Search Customization

### Index Schema

Modify the search index schema in `scripts/search_index/create_search_index.py`:

```python
fields = [
    SimpleField(name="id", type=SearchFieldDataType.String, key=True),
    SearchableField(name="content", type=SearchFieldDataType.String),
    SearchField(
        name="embedding",
        type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
        vector_search_dimensions=3072,
        vector_search_profile_name="vector-profile"
    ),
    # Add custom fields
    SimpleField(name="category", type=SearchFieldDataType.String, filterable=True),
    SimpleField(name="date", type=SearchFieldDataType.DateTimeOffset, sortable=True),
]
```

### Search Configuration

Customize search behavior:

```python
# Adjust hybrid search weights
vector_weight = 0.7
keyword_weight = 0.3

# Enable semantic ranking
semantic_config = SemanticConfiguration(
    name="semantic-config",
    prioritized_fields=SemanticPrioritizedFields(
        content_fields=[SemanticField(field_name="content")]
    )
)
```

## Prompt Engineering

### Query Prompts

Customize the RAG prompt in `scripts/search_index/create_knowledge_agent.py`:

```python
SYSTEM_PROMPT = """You are a helpful assistant that answers questions based on the provided documents.

Instructions:
- Only use information from the provided context
- Cite sources using [Source: filename] format
- If information is not found, say "I couldn't find this information in the documents"
- Be concise and specific

Context:
{context}
"""
```

### Extraction Prompts

Customize Vision AI prompts in `scripts/extraction/pdf_extraction_hybrid.py`:

```python
VISION_PROMPT = """Analyze this document page and extract:
1. All text content
2. Table data (in markdown format)
3. Diagram descriptions
4. Key metrics and values

Format the output in clean markdown.
"""
```

## Environment-Specific Configuration

### Development vs Production

Use environment variables for configuration:

```python
import os

DEBUG = os.getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL = os.getenv("PRISM_LOG_LEVEL", "INFO")
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", 50 * 1024 * 1024))
```

### Feature Flags

Implement feature flags:

```python
FEATURES = {
    "enable_vision": os.getenv("ENABLE_VISION", "true").lower() == "true",
    "enable_semantic_ranking": os.getenv("ENABLE_SEMANTIC", "true").lower() == "true",
}
```

## Integration Points

### Webhooks

Add webhook notifications:

```python
async def notify_webhook(event: str, data: dict):
    webhook_url = os.getenv("WEBHOOK_URL")
    if webhook_url:
        async with httpx.AsyncClient() as client:
            await client.post(webhook_url, json={"event": event, "data": data})
```

### External Storage

Replace file-based storage with Azure Blob Storage:

```python
from azure.storage.blob import BlobServiceClient

blob_client = BlobServiceClient.from_connection_string(
    os.getenv("AZURE_STORAGE_CONNECTION_STRING")
)

def upload_document(project: str, filename: str, content: bytes):
    container = blob_client.get_container_client(project)
    container.upload_blob(filename, content)
```

## Answer Evaluation

Prism includes an evaluation system using the Azure AI Evaluation SDK to assess answer quality.

### Evaluation Metrics

| Metric | Description |
|--------|-------------|
| **Relevance** | Does the answer address the question? |
| **Coherence** | Is the answer logically consistent? |
| **Fluency** | Is the language natural and readable? |
| **Groundedness** | Is the answer supported by the retrieved context? |

### Evaluation API

```python
# Evaluate all answers in a project
POST /api/evaluation/{project_id}/run

# Evaluate a single question
POST /api/evaluation/{project_id}/question
{
  "section_id": "tech-specs",
  "question_id": "q1"
}

# Get evaluation summary
GET /api/evaluation/{project_id}/summary
```

### Customizing Evaluation

The evaluation is powered by Azure AI Evaluation SDK. To customize:

```python
# scripts/evaluation/evaluate_results.py
from azure.ai.evaluation import (
    GroundednessEvaluator,
    RelevanceEvaluator,
    CoherenceEvaluator,
    FluencyEvaluator,
)

# Add custom evaluators or modify scoring logic
```

**Note**: Evaluation requires `azure-ai-evaluation` package and uses the same Azure OpenAI deployment as chat.

## Testing Customizations

Always write tests for custom code:

```python
# tests/test_custom_extractor.py
import pytest
from scripts.extraction.word_extraction import extract_word

def test_extract_word():
    result = extract_word(Path("tests/fixtures/sample.docx"))
    assert "expected content" in result
```

Run tests after changes:

```bash
pytest tests/
```
