# Data Ingestion

This guide covers supported document formats and the ingestion pipeline.

## Supported Formats

| Format | Extensions | Extraction Method |
|--------|------------|-------------------|
| PDF | `.pdf` | PyMuPDF4LLM + Vision AI |
| Excel | `.xlsx`, `.xlsm` | openpyxl + AI enhancement |
| Email | `.msg` | extract-msg + AI enhancement |
| Images | `.png`, `.jpg`, `.jpeg` | Vision AI |

## Document Upload

### Via UI

1. Navigate to your project
2. Drag and drop files into the upload area
3. Or click to browse and select files
4. Multiple files can be uploaded at once

### Via API

```bash
curl -X POST "http://localhost:8000/api/projects/{project}/files" \
  -H "Authorization: Bearer {token}" \
  -F "files=@document.pdf"
```

### Via CLI

Place files directly in the project's documents folder:
```bash
cp document.pdf projects/myproject/documents/
```

## PDF Processing

### Hybrid Extraction

Prism uses a hybrid approach for PDFs that balances cost and quality:

1. **Text Extraction (PyMuPDF4LLM)**
   - Fast, local processing
   - No API costs
   - Extracts text, tables, and structure

2. **Vision AI (Azure OpenAI)**
   - Processes pages with images/diagrams
   - Interprets visual content
   - Only used when needed (cost optimization)

### How It Works

```
For each page in PDF:
  1. Extract text with PyMuPDF4LLM
  2. Check if page has images/diagrams
  3. If visual content exists:
     - Send to Vision AI for interpretation
     - Merge with text extraction
  4. If text-only:
     - Use text extraction only (skip Vision)
```

### Configuration

Project-specific extraction instructions in `config.json`:

```json
{
  "extraction_instructions": "Focus on technical specifications. Extract all measurements and standards references."
}
```

## Excel Processing

### Extraction Method

1. **openpyxl** reads spreadsheet structure
2. Tables are converted to markdown
3. AI enhancement adds context and descriptions

### Best Practices

- Use clear headers in row 1
- Avoid merged cells when possible
- Keep related data in contiguous ranges
- Name sheets descriptively

### Limitations

- Very large spreadsheets may be truncated
- Complex formulas are not evaluated
- Charts/graphs are not extracted

## Email Processing

### Extraction Method

1. **extract-msg** parses .msg files
2. Extracts: sender, recipients, subject, body, attachments
3. AI enhancement summarizes and structures content

### Attachment Handling

- Attachments are extracted and processed separately
- Supported attachment types follow the main format list
- Nested emails are flattened

## Incremental Processing

Prism tracks extraction status per document to avoid reprocessing:

### Status Tracking

`output/extraction_status.json`:
```json
{
  "document1.pdf": {
    "status": "completed",
    "timestamp": "2024-01-15T10:30:00Z",
    "output_file": "document1.md"
  },
  "document2.xlsx": {
    "status": "completed",
    "timestamp": "2024-01-15T10:31:00Z",
    "output_file": "document2.md"
  }
}
```

### Behavior

- **New documents**: Automatically processed
- **Already processed**: Skipped (saves time and cost)
- **Force re-run**: Use "Re-run" button to process all

### When to Re-run

- Extraction instructions changed
- Document was updated
- Previous extraction had errors
- Testing different approaches

## Chunking

After extraction, documents are chunked for optimal retrieval:

### Chunking Strategy

- **Page-aware splitting**: Documents split by structure first (pages, sheets, email parts)
- **Chunk size**: ~1000 tokens
- **Overlap**: 200 tokens between chunks
- **Boundaries**: Respects markdown headers within each section

### Contextual Chunk Enrichment

Each chunk is enriched with context for better embedding quality:

```
Document: Technical Manual
Section: Safety Requirements > Electrical Standards
Location: Page 5

[actual chunk content here...]
```

This context prefix helps the embedding model understand WHERE the content comes from, improving retrieval accuracy.

### Chunk Metadata

Each chunk includes:
```json
{
  "chunk_id": "a1b2c3d4_chunk_000",
  "content": "original chunk text...",
  "enriched_content": "Document: ...\nSection: ...\n\noriginal chunk text...",
  "source_file": "document1.pdf",
  "location": "Page 1",
  "section_title": "Introduction",
  "section_hierarchy": {"Header 1": "Chapter 1", "Header 2": "Introduction"}
}
```

The `location` field format varies by document type:
- **PDFs**: "Page 1", "Page 2", etc.
- **Excel**: "Sheet: Sales", "Sheet: Data", etc.
- **Email**: "Email Metadata", "Email Body"

## Embedding

Chunks are embedded using Azure OpenAI's text-embedding-3-large model:

### Embedding Details

- **Model**: text-embedding-3-large
- **Dimensions**: 1024
- **Batch processing**: 100 chunks per batch
- **Input**: Enriched content (includes context prefix for better retrieval)

### Storage

Embeddings are stored in `output/embedded_documents/`:
```json
{
  "id": "doc1_chunk_0",
  "content": "chunk text...",
  "embedding": [0.123, -0.456, ...],
  "metadata": {...}
}
```

## Indexing

### Index Schema

Azure AI Search index includes:

| Field | Type | Purpose |
|-------|------|---------|
| id | string | Unique chunk ID |
| content | string | Chunk text (searchable) |
| embedding | vector | For vector search |
| source_document | string | Original filename |
| location | string | Document location (Page N, Sheet: Name, etc.) |
| section | string | Section header |

### Search Capabilities

- **Vector search**: Semantic similarity
- **Keyword search**: BM25 full-text
- **Hybrid search**: Combined ranking
- **Semantic ranking**: Re-ranking with AI

## Running the Pipeline

### Via UI (Recommended)

1. Navigate to your project in the web UI
2. Go to the **Pipeline** view
3. Click each stage button in order:
   - **Process** - Extract documents to markdown
   - **Deduplicate** - Remove duplicate content
   - **Chunk** - Split into searchable chunks
   - **Embed** - Generate vector embeddings
   - **Index Create** - Create Azure AI Search index
   - **Index Upload** - Upload chunks to search index
   - **Create Agent** - Create Knowledge Agent for querying

### Force Re-run

Use the **Re-run** button in the Pipeline view to re-process documents that have already been processed. This is useful when:
- Extraction instructions changed
- Documents were updated
- Previous extraction had errors

## Troubleshooting

### Document Won't Extract

1. Check file is not corrupted (open locally)
2. Ensure file format is supported
3. Check Azure OpenAI quota for Vision calls
4. Review extraction logs for errors

### Poor Extraction Quality

1. Try adding extraction instructions
2. For PDFs, ensure text is selectable (not scanned)
3. For complex documents, consider pre-processing

### Chunking Issues

1. Very long documents may timeout
2. Try reducing chunk size
3. Check for encoding issues in source

See [Troubleshooting](troubleshooting.md) for more solutions.
