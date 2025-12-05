# Architecture

Prism is a document intelligence platform that transforms unstructured documents into queryable knowledge using a hybrid local + cloud approach.

## System Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              Frontend (Vue 3)                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │Dashboard │  │ Projects │  │  Query   │  │Workflows │  │ Results  │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└─────────────────────────────────┬────────────────────────────────────────────┘
                                  │ REST API
┌─────────────────────────────────┼────────────────────────────────────────────┐
│                         FastAPI Backend                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Project    │  │   Pipeline   │  │   Workflow   │  │    Query     │     │
│  │   Service    │  │   Service    │  │   Service    │  │   Service    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘     │
│                              │                                               │
│                    ┌─────────┴─────────┐                                    │
│                    │  Storage Service  │                                    │
│                    └─────────┬─────────┘                                    │
└──────────────────────────────┼──────────────────────────────────────────────┘
       │                       │                   │                   │
       ▼                       ▼                   ▼                   ▼
┌──────────────┐        ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Azure Blob   │        │ Local Libs   │    │  Azure AI    │    │ Azure OpenAI │
│ Storage /    │        │ (Extraction) │    │   Search     │    │  (GPT-4.1)   │
│ Azurite      │        └──────────────┘    └──────────────┘    └──────────────┘
└──────────────┘
```

## Document Processing Layer

### Hybrid Extraction Strategy

Prism uses local libraries first, then AI only when necessary:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Document Extraction                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  PDF Files                                                               │
│  ─────────                                                               │
│  ┌────────────────────┐     ┌────────────────────┐                      │
│  │    PyMuPDF4LLM     │────▶│  Structured        │                      │
│  │  (Local, Free)     │     │  Markdown          │                      │
│  │  • Text extraction │     │  + Tables          │                      │
│  │  • Table detection │     └─────────┬──────────┘                      │
│  │  • Layout analysis │               │                                  │
│  └────────────────────┘               │                                  │
│                                       ▼                                  │
│                          ┌────────────────────────┐                      │
│                          │  Has images/diagrams?  │                      │
│                          └───────────┬────────────┘                      │
│                                      │                                   │
│                         ┌────────────┴────────────┐                      │
│                         │                         │                      │
│                        Yes                        No                     │
│                         │                         │                      │
│                         ▼                         │                      │
│              ┌────────────────────┐               │                      │
│              │   GPT-4.1 Vision   │               │                      │
│              │   (Validation)     │               │                      │
│              │  • Image analysis  │               │                      │
│              │  • Diagram reading │               │                      │
│              └─────────┬──────────┘               │                      │
│                        │                          │                      │
│                        └──────────┬───────────────┘                      │
│                                   ▼                                      │
│                          ┌────────────────┐                              │
│                          │ Final Markdown │                              │
│                          └────────────────┘                              │
│                                                                          │
│  Excel Files                                                             │
│  ───────────                                                             │
│  ┌────────────────────┐     ┌────────────────────┐     ┌──────────────┐ │
│  │     openpyxl       │────▶│   AI Enhancement   │────▶│   Markdown   │ │
│  │  • All worksheets  │     │  • Categorization  │     │   + Tables   │ │
│  │  • Formulas        │     │  • Standards refs  │     └──────────────┘ │
│  │  • Merged cells    │     │  • Validation      │                      │
│  └────────────────────┘     └────────────────────┘                      │
│                                                                          │
│  Email Files (.msg)                                                      │
│  ──────────────────                                                      │
│  ┌────────────────────┐     ┌────────────────────┐     ┌──────────────┐ │
│  │    extract-msg     │────▶│   AI Enhancement   │────▶│   Markdown   │ │
│  │  • Headers         │     │  • Categorization  │     │   + Metadata │ │
│  │  • Body            │     │  • Action items    │     └──────────────┘ │
│  │  • Attachments     │     │  • Deadlines       │                      │
│  └────────────────────┘     └────────────────────┘                      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Why Hybrid?

| Approach | Cost | Speed | Quality |
|----------|------|-------|---------|
| Vision-only | $$$$ | Slow | High |
| Local-only | Free | Fast | Medium |
| **Hybrid** | $ | Fast | High |

- **70%+ cost reduction** vs full-vision approaches
- Local extraction handles text-heavy pages instantly
- Vision validates complex pages with images/diagrams
- Repeated images (logos, headers) auto-filtered to avoid redundant API calls

## RAG Pipeline

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              RAG Pipeline                                     │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   │
│  │  DEDUPLICATE│───▶│    CHUNK    │───▶│    EMBED    │───▶│    INDEX    │   │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘   │
│        │                  │                  │                  │            │
│        ▼                  ▼                  ▼                  ▼            │
│   SHA256 hash       MarkdownHeader      text-embedding     Azure AI         │
│   Newest wins       TextSplitter        -3-large           Search           │
│                     tiktoken            1024 dims          Hybrid Index     │
│                     400-1000 tokens     Batch: 100                          │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Stage Details

**Deduplicate**
- SHA256 content hashing
- Keeps newest version by modification time
- Outputs document inventory for downstream stages

**Chunk**
- LangChain MarkdownHeaderTextSplitter respects document structure
- Token counting with tiktoken (matches OpenAI tokenizer)
- Target: 1000 tokens, Min: 400 tokens, Overlap: 200 tokens
- Preserves section titles as metadata

**Embed**
- Azure OpenAI text-embedding-3-large
- 1024 dimensions
- Batch processing (100 chunks/batch)
- Resume capability for interrupted runs

**Index**
- Azure AI Search with hybrid search
- Vector field (HNSW algorithm)
- Keyword field (BM25)
- Semantic ranking enabled

## Azure AI Search Knowledge Agents

Prism uses [Azure AI Search Knowledge Agents](https://learn.microsoft.com/azure/search/search-knowledge-agent) for intelligent document retrieval:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         Azure AI Search                                       │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         Search Index                                 │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │    │
│  │  │ chunk_id │ │ content  │ │ vector   │ │source_file│ │page_number│  │    │
│  │  │  (key)   │ │(keyword) │ │ (1024D)  │ │(filter)   │ │ (sort)    │  │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                    │                                          │
│                                    ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                       Knowledge Source                               │    │
│  │  • Wraps index for agent access                                     │    │
│  │  • Configures retrievable fields                                    │    │
│  │  • Sets reranker threshold (2.0)                                    │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                    │                                          │
│                                    ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                       Knowledge Agent                                │    │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐        │    │
│  │  │ Query Planning │─▶│ Parallel Search │─▶│Answer Synthesis│        │    │
│  │  │                │  │                 │  │  + Citations   │        │    │
│  │  │ Breaks complex │  │ Focused sub-   │  │                │        │    │
│  │  │ questions into │  │ queries across │  │ Grounded in    │        │    │
│  │  │ subqueries     │  │ index          │  │ retrieved docs │        │    │
│  │  └────────────────┘  └────────────────┘  └────────────────┘        │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Knowledge Agent Capabilities

1. **Query Planning**: Analyzes user question and generates focused subqueries
2. **Parallel Retrieval**: Executes subqueries simultaneously
3. **Answer Synthesis**: Combines results into coherent answer
4. **Citation Tracking**: Returns source documents with page numbers and relevance scores
5. **Activity Logging**: Shows query planning steps for transparency

### Grounding Instructions

The agent is configured with strict grounding:

```
- ONLY answer using explicitly stated document content
- NEVER use general knowledge or inference
- ALWAYS cite documents with page/section numbers
- Mark assumptions explicitly (ASSUMPTION: prefix)
- Distinguish "NOT FOUND" vs "EXPLICITLY EXCLUDED"
```

## Workflow System

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           Workflow System                                     │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  workflow_config.json                                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ {                                                                    │    │
│  │   "sections": [                                                      │    │
│  │     {                                                                │    │
│  │       "id": "tech-specs",                                           │    │
│  │       "name": "Technical Specifications",                           │    │
│  │       "template": "Answer based on technical documents...",         │    │
│  │       "questions": [                                                │    │
│  │         { "question": "Rated voltage?", "instructions": "..." },    │    │
│  │         { "question": "Temperature range?", "instructions": "..." } │    │
│  │       ]                                                             │    │
│  │     }                                                               │    │
│  │   ]                                                                 │    │
│  │ }                                                                   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                          │
│                                    ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      Workflow Execution                              │    │
│  │                                                                      │    │
│  │  For each section:                                                  │    │
│  │    Agent Prompt = Section Template + Question Instructions          │    │
│  │                                                                      │    │
│  │  For each question:                                                 │    │
│  │    1. Build prompt                                                  │    │
│  │    2. Query Knowledge Agent                                         │    │
│  │    3. Parse citations                                               │    │
│  │    4. Save result                                                   │    │
│  │    5. Update progress                                               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                          │
│                                    ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         Results                                      │    │
│  │  • Answer text                                                      │    │
│  │  • Source citations with page numbers                               │    │
│  │  • Relevance scores                                                 │    │
│  │  • Export to CSV                                                    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Complete Pipeline

```
User uploads PDF/Excel/Email
          │
          ▼
┌─────────────────────┐
│ Local Extraction    │ ◀── PyMuPDF4LLM, openpyxl, extract-msg
│ (Free, Fast)        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ AI Enhancement      │ ◀── GPT-4.1 Vision (if needed)
│ (Cost Optimized)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Structured Markdown │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Deduplicate (SHA256)│
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Chunk (tiktoken)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Embed (3-large)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Azure AI Search     │
│ Index + Source +    │
│ Knowledge Agent     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Query / Workflows   │
│ Answers + Citations │
└─────────────────────┘
```

## Project Isolation

Each project is fully isolated in Azure Blob Storage:

```
Container: prism-projects
├── project-a/
│   ├── documents/           # Uploaded files
│   ├── output/
│   │   ├── extraction_results/*.md
│   │   ├── extraction_status.json
│   │   ├── chunked_documents/*.json
│   │   ├── embedded_documents/*.json
│   │   └── results.json     # Workflow answers + evaluations
│   ├── config.json          # Extraction instructions
│   └── workflow_config.json # Q&A templates
│
├── project-b/
│   └── (same structure)
```

**Storage:**
- Production: Azure Blob Storage
- Local Development: Azurite (Azure Storage emulator)

**Azure Search resources per project:**
- Index: `prism-{project}-index`
- Knowledge Source: `prism-{project}-index-source`
- Knowledge Agent: `prism-{project}-index-agent`

## Azure Services

| Service | Purpose | Configuration |
|---------|---------|---------------|
| **Azure OpenAI** | GPT-4.1 (extraction, chat), Vision, text-embedding-3-large | AI Foundry deployment |
| **Azure AI Search** | Vector + keyword hybrid search, semantic ranking, Knowledge Agents | Basic tier minimum |
| **Container Apps** | Serverless hosting | Consumption plan |
| **Container Registry** | Container images | Basic tier |
| **Application Insights** | Monitoring | Log Analytics workspace |

## Security Considerations

- **Authentication**: Password-based (upgrade to Entra ID for production)
- **API Keys**: Environment variables / Container App secrets
- **Data**: Stored in Azure-hosted containers
- **Network**: HTTPS for all external communication

See [Productionizing](productionizing.md) for production security recommendations.

## Scalability

- **Stateless Backend**: Container Apps can scale horizontally
- **Async Processing**: Long operations run asynchronously
- **Incremental Processing**: Only new documents are processed
- **Resume Capability**: Embedding generation resumes from last checkpoint
