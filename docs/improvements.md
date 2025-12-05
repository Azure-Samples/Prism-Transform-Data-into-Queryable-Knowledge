# Pipeline Improvements

Identified improvements to the document extraction and RAG pipeline based on analysis of RFP technical content extraction quality.

---

## 1. Vision for Vector Diagrams

**Priority:** High
**Files:** `scripts/extraction/pdf_extraction_hybrid.py`

### Problem

`analyze_page()` only triggers Vision when `page.get_images()` returns embedded raster images. Engineering drawings (SLDs, P&IDs, protection schemes) are often pure vector graphics (`page.get_drawings()`) which get skipped. This results in diagram pages having only OCR text with no semantic description.

### Current Logic

```python
# Line 223 in pdf_extraction_hybrid.py
needs_vision = has_images  # Only true for embedded raster images
```

### Solution

Detect "diagram pages" by heuristic - high vector count combined with low text density indicates a drawing, not a table:

```python
def analyze_page(page, local_markdown, repeated_xrefs=None):
    images = page.get_images()
    drawings = page.get_drawings()

    # Filter repeated images (logos/headers)
    real_images = [img for img in images if img[0] not in (repeated_xrefs or set())]

    has_images = len(real_images) > 0
    has_complex_drawings = len(drawings) > 50

    # NEW: Detect diagram pages (lots of vectors, little text)
    text_length = len(local_markdown.strip())
    is_likely_diagram = (
        has_complex_drawings and
        text_length < 500 and  # Very little extracted text
        len(drawings) > 100    # But many vector elements
    )

    # Trigger Vision for images OR likely diagrams
    needs_vision = has_images or is_likely_diagram

    if is_likely_diagram and not has_images:
        reason = f"Vector diagram detected ({len(drawings)} drawings, {text_length} chars text)"
    elif has_images:
        reason = f"Page has {len(real_images)} content image(s)"
    else:
        reason = "Text-only page"

    return PageAnalysis(
        has_images=has_images,
        has_complex_drawings=has_complex_drawings,
        image_count=len(real_images),
        drawing_count=len(drawings),
        text_length=text_length,
        needs_vision=needs_vision,
        reason=reason
    )
```

### Tuning Notes

- Thresholds (500 chars, 100 drawings) may need adjustment based on testing
- Consider adding aspect ratio check - diagram pages tend to be landscape
- May want to add a cost control flag to disable this for large batches

---

## 2. Excel Structure Preservation

**Priority:** High
**Files:** `scripts/extraction/excel_extraction_agents.py`

### Problem

Current Excel extraction uses LLM to generate a JSON summary, losing actual row/column data. For a BOQ with 4000+ line items, you can't search for specific item numbers or quantities.

### Solution

Two-pass extraction that preserves structure while adding semantic enrichment:

**Pass 1 - Structural extraction (no LLM):**

```python
def extract_excel_structured(file_path: Path) -> str:
    """Extract Excel as markdown tables, preserving all rows/columns."""
    wb = openpyxl.load_workbook(file_path, data_only=True)
    markdown_parts = []

    for sheet_name in wb.sheetnames:
        sheet = wb[sheet_name]
        markdown_parts.append(f"## Sheet: {sheet_name}\n")

        # Find data boundaries (skip empty rows/cols)
        data = []
        for row in sheet.iter_rows(values_only=True):
            if any(cell is not None for cell in row):
                data.append(row)

        if not data:
            markdown_parts.append("*(Empty sheet)*\n")
            continue

        # Convert to markdown table
        headers = [str(cell) if cell else "" for cell in data[0]]
        markdown_parts.append("| " + " | ".join(headers) + " |")
        markdown_parts.append("| " + " | ".join(["---"] * len(headers)) + " |")

        for row in data[1:]:
            cells = [str(cell) if cell else "" for cell in row]
            markdown_parts.append("| " + " | ".join(cells) + " |")

        markdown_parts.append("")

    return "\n".join(markdown_parts)
```

**Pass 2 - LLM enhancement (optional):**

```python
def enhance_excel_metadata(structured_markdown: str) -> dict:
    """Use LLM to extract metadata/summary, but keep structured data."""
    return {
        "structured_content": structured_markdown,  # Full table data
        "metadata": llm_generated_summary,          # Semantic enrichment
        "key_requirements": extracted_requirements
    }
```

### Output Format

```markdown
## Sheet: Schedule 1D - Foreign Supply

| Item | Description | Unit | Qty | Unit Price | Total |
|------|-------------|------|-----|------------|-------|
| 1.1 | 400kV SF6 Circuit Breaker | Set | 13 | | |
| 1.2 | 400kV Disconnector with ES | Set | 26 | | |
...

## Metadata (LLM-extracted)
- Equipment types: SF6 Circuit Breaker, Disconnector, CVT...
- Voltage levels: 400kV, 230kV, 132kV
```

---

## 3. Table-Aware Chunking

**Priority:** Medium
**Files:** `scripts/rag/chunk_documents.py`

### Problem

`RecursiveCharacterTextSplitter` can split markdown tables mid-row:

```markdown
| Item | Description | Qty |
|------|-------------|-----|
| 1.1 | SF6 Circuit  |     <- CHUNK BOUNDARY HERE
Breaker 400kV | 13 |
```

### Solution

Pre-process markdown to protect tables, then chunk, then restore:

```python
import re

def protect_tables(markdown: str) -> tuple[str, dict]:
    """Replace tables with placeholders, return mapping."""
    table_pattern = r'(\|[^\n]+\|\n\|[-:| ]+\|\n(?:\|[^\n]+\|\n)*)'
    tables = {}

    def replace_table(match):
        table_id = f"__TABLE_{len(tables)}__"
        tables[table_id] = match.group(0)
        return f"\n{table_id}\n"

    protected = re.sub(table_pattern, replace_table, markdown)
    return protected, tables

def restore_tables(chunks: list[str], tables: dict) -> list[str]:
    """Restore table placeholders in chunks."""
    restored = []
    for chunk in chunks:
        for table_id, table_content in tables.items():
            chunk = chunk.replace(table_id, table_content)
        restored.append(chunk)
    return restored

def chunk_with_table_protection(markdown: str, chunk_size: int, overlap: int):
    """Chunk markdown while keeping tables intact."""
    protected_md, tables = protect_tables(markdown)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = splitter.split_text(protected_md)

    final_chunks = restore_tables(chunks, tables)
    final_chunks = handle_large_tables(final_chunks, chunk_size)

    return final_chunks

def handle_large_tables(chunks: list[str], chunk_size: int) -> list[str]:
    """Split chunks that exceed size due to large tables."""
    result = []
    for chunk in chunks:
        if len(chunk) <= chunk_size * 1.5:  # Allow some overflow for table integrity
            result.append(chunk)
        else:
            result.extend(split_large_table_chunk(chunk, chunk_size))
    return result

def split_large_table_chunk(chunk: str, chunk_size: int) -> list[str]:
    """Split oversized table by rows, repeating header in each chunk."""
    lines = chunk.split('\n')

    header_lines = []
    data_lines = []
    in_table = False

    for line in lines:
        if line.startswith('|'):
            if not in_table:
                in_table = True
                header_lines = [line]
            elif line.startswith('|--') or line.startswith('| --'):
                header_lines.append(line)
            else:
                data_lines.append(line)
        else:
            if not in_table:
                header_lines.append(line)

    header = '\n'.join(header_lines)
    header_size = len(header)
    available = chunk_size - header_size - 100

    chunks = []
    current_rows = []
    current_size = 0

    for row in data_lines:
        if current_size + len(row) > available and current_rows:
            chunks.append(header + '\n' + '\n'.join(current_rows))
            current_rows = [row]
            current_size = len(row)
        else:
            current_rows.append(row)
            current_size += len(row) + 1

    if current_rows:
        chunks.append(header + '\n' + '\n'.join(current_rows))

    return chunks
```

---

## 4. Full Section Hierarchy

**Priority:** Medium
**Files:** `scripts/rag/chunk_documents.py`

### Problem

Current chunks only capture headers the splitter actually splits on:

```json
"section_hierarchy": {"Header 1": "BIDDING DOCUMENT"}
```

But documents have deep nesting like `5.1.2.3 IEC 61850 Communication` that's lost.

### Solution

Parse full hierarchy before chunking, propagate to all child chunks:

```python
import re

def parse_section_hierarchy(markdown: str) -> list[dict]:
    """Parse all headers with their positions and levels."""
    header_pattern = r'^(#{1,6})\s+(.+)$'
    headers = []

    for i, line in enumerate(markdown.split('\n')):
        match = re.match(header_pattern, line)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            headers.append({
                'level': level,
                'title': title,
                'line': i,
                'char_offset': sum(len(l) + 1 for l in markdown.split('\n')[:i])
            })

    return headers

def get_hierarchy_at_position(headers: list[dict], char_position: int) -> dict:
    """Get full header hierarchy at a given character position."""
    relevant_headers = [h for h in headers if h['char_offset'] <= char_position]

    hierarchy = {}
    for header in relevant_headers:
        level = header['level']
        hierarchy[f"h{level}"] = header['title']
        for deeper in range(level + 1, 7):
            hierarchy.pop(f"h{deeper}", None)

    return hierarchy

def build_hierarchy_path(hierarchy: dict) -> str:
    """Convert hierarchy dict to readable path."""
    parts = []
    for level in range(1, 7):
        if f"h{level}" in hierarchy:
            parts.append(hierarchy[f"h{level}"])
    return " > ".join(parts)

def enrich_chunk_with_hierarchy(chunk: dict, headers: list[dict], chunk_start_offset: int):
    """Add full hierarchy to chunk metadata."""
    hierarchy = get_hierarchy_at_position(headers, chunk_start_offset)

    chunk['section_hierarchy'] = hierarchy
    chunk['section_path'] = build_hierarchy_path(hierarchy)

    if hierarchy:
        chunk['enriched_content'] = (
            f"Document: {chunk['source_file']}\n"
            f"Section: {chunk.get('section_path', '')}\n"
            f"Location: {chunk.get('location', '')}\n\n"
            f"{chunk['content']}"
        )

    return chunk
```

### Result

```json
{
  "chunk_id": "abc123_chunk_050",
  "content": "The IEC 61850 communication system shall...",
  "section_hierarchy": {
    "h1": "Volume 2 - Technical Specifications",
    "h2": "Section 5 - Substation Automation",
    "h3": "5.1 Communication Requirements",
    "h4": "5.1.2 Protocol Standards",
    "h5": "5.1.2.3 IEC 61850 Communication"
  },
  "section_path": "Volume 2 > Section 5 > 5.1 Communication > 5.1.2 Protocol Standards > 5.1.2.3 IEC 61850"
}
```

---

## 5. Chunk-Level Deduplication

**Priority:** Medium
**Files:** `scripts/rag/deduplicate_documents.py` (new function) or `scripts/rag/chunk_documents.py`

### Problem

Same boilerplate appears in multiple documents (legal disclaimers, standard definitions, headers). Creates redundant chunks that dilute search relevance and waste embedding API calls.

### Solution

Content-hash deduplication with first-occurrence tracking:

```python
import hashlib
from collections import defaultdict

def deduplicate_chunks(chunks: list[dict], similarity_threshold: float = 0.95) -> list[dict]:
    """Remove duplicate chunks, keeping first occurrence with source tracking."""

    seen_hashes = {}
    deduplicated = []
    duplicate_count = 0

    for chunk in chunks:
        # Normalize content for hashing
        normalized = ' '.join(chunk['content'].lower().split())
        content_hash = hashlib.md5(normalized.encode()).hexdigest()

        if content_hash in seen_hashes:
            # Duplicate - add source to original's duplicate_sources
            original = seen_hashes[content_hash]
            if 'duplicate_sources' not in original:
                original['duplicate_sources'] = []
            original['duplicate_sources'].append({
                'source_file': chunk['source_file'],
                'location': chunk.get('location', '')
            })
            duplicate_count += 1
        else:
            # First occurrence - keep it
            seen_hashes[content_hash] = chunk
            deduplicated.append(chunk)

    logger.info(f"Deduplication: {len(chunks)} -> {len(deduplicated)} chunks ({duplicate_count} duplicates removed)")

    return deduplicated
```

### Optional: Fuzzy Deduplication

For near-duplicates (minor wording variations), use MinHash/LSH:

```python
def fuzzy_deduplicate(chunks: list[dict], threshold: float = 0.9) -> list[dict]:
    """Remove near-duplicate chunks using MinHash/LSH."""
    from datasketch import MinHash, MinHashLSH

    lsh = MinHashLSH(threshold=threshold, num_perm=128)
    seen = {}
    deduplicated = []

    for i, chunk in enumerate(chunks):
        mh = MinHash(num_perm=128)
        for word in chunk['content'].lower().split():
            mh.update(word.encode('utf-8'))

        chunk_id = f"chunk_{i}"
        similar = lsh.query(mh)

        if not similar:
            lsh.insert(chunk_id, mh)
            seen[chunk_id] = chunk
            deduplicated.append(chunk)
        else:
            original_id = similar[0]
            if 'near_duplicates' not in seen[original_id]:
                seen[original_id]['near_duplicates'] = []
            seen[original_id]['near_duplicates'].append(chunk['source_file'])

    return deduplicated
```

### Integration Point

Run after chunking, before embedding generation:

```
Extract → Chunk → **Deduplicate** → Embed → Index
```

### Dependencies

For fuzzy deduplication:
```
pip install datasketch
```

---

## Implementation Order

Recommended order based on impact and dependencies:

1. **Vision for Vector Diagrams** - High impact for engineering drawings
2. **Excel Structure Preservation** - High impact for BOQ searchability
3. **Chunk-Level Deduplication** - Reduces noise, saves embedding costs
4. **Table-Aware Chunking** - Improves chunk quality
5. **Full Section Hierarchy** - Better context for retrieval

---

## Testing Plan

For each improvement:

1. Run extraction on `fromblob/rfp3/documents/` test set
2. Compare output quality before/after
3. Verify chunk metadata correctness
4. Test search relevance with sample queries
5. Measure any cost/performance impact
