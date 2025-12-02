# Prism User Guide

Complete guide to using Prism for document extraction and knowledge querying.

## Overview

Prism transforms unstructured documents into searchable, queryable knowledge. It supports:

- **PDF files** - Technical documents, specifications, reports
- **Excel files** - Spreadsheets, data tables
- **Email files** - .msg email archives with attachments

## Core Concepts

### Projects

A project is a container for related documents. Each project has:

- **Documents** - Uploaded source files
- **Output** - Extracted and processed content
- **Workflow Config** - Custom question sections
- **Search Index** - Azure AI Search index
- **Knowledge Agent** - AI query interface

### Pipeline

The processing pipeline transforms raw documents into queryable knowledge:

```
Upload → Process → Deduplicate → Chunk → Embed → Index → Agent → Query
```

### Workflows

Workflows are structured question sets for systematically extracting information:

- **Sections** - Groups of related questions (e.g., "Technical Specs")
- **Questions** - Individual queries with instructions
- **Templates** - Section-level prompts that guide the AI

## Getting Started

### 1. Login

Navigate to http://localhost:3000 and enter your password.

### 2. Create a Project

1. Go to **Projects**
2. Click **New Project**
3. Enter a descriptive name (e.g., "vendor-proposal-2024")
4. Click **Create**

### 3. Upload Documents

1. Open your project
2. Use the upload area to add files:
   - Drag and drop multiple files
   - Or click to browse
3. Supported formats: PDF, XLSX, XLSM, MSG

### 4. Run the Pipeline

Execute each pipeline stage in order:

| Stage | Description | Output |
|-------|-------------|--------|
| Process | Extract text and images from documents | Markdown files |
| Deduplicate | Identify and remove duplicate content | Clean content |
| Chunk | Split into semantic chunks for search | JSON chunks |
| Embed | Generate vector embeddings | Embedded chunks |
| Index Create | Create Azure AI Search index | Search index |
| Index Upload | Upload chunks to search index | Indexed content |
| Source Create | Create knowledge source wrapper | Knowledge source |
| Agent Create | Create knowledge retrieval agent | Ready for queries |

Click **Run** on each step, or **Run All** for the full pipeline.

### Incremental Processing

Prism tracks which documents have already been extracted. When you run the "Process" stage:

- **Already-extracted documents are skipped** - Saves time and API costs
- **Only new documents are processed** - Add documents incrementally
- **Use "Re-run" to force re-extraction** - Click the "Re-run" button to re-process all documents

The extraction status is tracked in `output/extraction_status.json`.

### 5. Query Documents

Once the pipeline is complete:

1. Go to **Query**
2. Select your project
3. Type a natural language question
4. Get AI-generated answers with source citations

## Configuring Workflows

### Adding Sections

1. Open your project
2. Click **Configure Workflow**
3. Click **Add Section**
4. Enter:
   - **Name** - Section title (e.g., "Technical Specifications")
   - **Template** - Instructions for the AI

Example template:
```
Answer the following question based on the technical documents.
Focus on specific values, measurements, and standards references.
If the information is not found, state "Not specified in documents."
```

### Adding Questions

1. Expand a section
2. Click **Add Question**
3. Enter:
   - **Question** - The query to answer
   - **Instructions** - Specific guidance for this question

Example:
- Question: "What is the rated voltage?"
- Instructions: "Look for voltage ratings in electrical specifications. Include all voltage levels if multiple exist."

### Running Workflows

1. Go to **Workflows**
2. Select a section
3. Click **Run Section**
4. Monitor progress in real-time
5. View results when complete

## Viewing Results

### Results Page

- View all answered questions
- Filter by section
- See completion percentage
- Export to CSV

### Result Details

Each result shows:
- **Question** - The original query
- **Answer** - AI-generated response
- **References** - Source document citations
- **Comments** - Additional notes

## API Access

Prism provides a REST API for programmatic access:

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/projects` | GET | List all projects |
| `/api/projects` | POST | Create a project |
| `/api/projects/{id}` | GET | Get project details |
| `/api/projects/{id}` | DELETE | Delete a project |
| `/api/projects/{id}/files` | GET | List project files |
| `/api/projects/{id}/files` | POST | Upload files |
| `/api/pipeline/stages` | GET | List pipeline stages |
| `/api/pipeline/{id}/run` | POST | Run a pipeline stage |
| `/api/query` | POST | Query documents |

### API Documentation

Interactive API docs available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Best Practices

### Document Preparation

- Use clear, descriptive filenames
- Ensure PDFs have selectable text (not scanned images)
- Organize related documents in the same project

### Question Design

- Be specific in your questions
- Include context in instructions
- Use consistent terminology
- Group related questions in sections

### Performance Tips

- Process documents in batches
- Use focused, specific queries
- Create targeted sections for different topics

## Troubleshooting

### Pipeline Fails

1. Check Azure credentials in `.env`
2. Verify documents are valid and not corrupted
3. Check backend logs: `docker-compose -f infra/docker/docker-compose.yml logs backend`

### Poor Query Results

1. Verify pipeline completed successfully
2. Check if documents contain the information
3. Try rephrasing the question
4. Add more specific instructions

### Slow Processing

1. Large documents take longer to process
2. Check Azure service quotas
3. Consider splitting very large files

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Enter` | Submit query |
| `Escape` | Close modal |

## Data Storage

All data is stored in the `projects/` directory:

```
projects/
  {project-name}/
    config.json             # Project settings (extraction instructions)
    documents/              # Uploaded files
    output/                 # Processed content
      extraction_results/   # Extracted markdown
      extraction_status.json# Per-document extraction tracking
      chunked_documents/    # JSON chunks
      embedded_documents/   # With embeddings
      results.json          # Workflow answers
    workflow_config.json    # Sections & questions
```

## Security Notes

- All queries use Azure AI services
- Documents remain in your Azure subscription
- API protected by password authentication
- HTTPS recommended for production

## Getting Help

- Check logs: `docker-compose -f infra/docker/docker-compose.yml logs`
- API docs: http://localhost:8000/docs
- See [QUICKSTART.md](QUICKSTART.md) for setup
- Review [CLAUDE.md](../CLAUDE.md) for architecture
