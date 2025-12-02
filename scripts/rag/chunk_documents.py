"""
Chunk deduplicated markdown documents using semantic/structure-aware strategies.

This script uses LangChain's MarkdownHeaderTextSplitter for structure-aware chunking,
preserving document hierarchy while staying within token limits.

Strategy:
1. Load deduplicated documents from inventory
2. Remove page marker headers (redundant metadata)
3. Split by markdown headers (##, ###, etc.)
4. Merge small adjacent sections to reach 400+ token minimum
5. Sub-chunk oversized sections to ~1000 tokens
6. Add 200-token overlap for context (20% of target)
7. Filter chunks < 200 tokens (would be mostly overlap)
8. Extract metadata (source file, page numbers, sections)

Usage:
    python main.py chunk --project myproject

Output:
    - projects/{project}/output/chunked_documents/{chunk_id}.json - Individual chunk files
    - projects/{project}/output/chunked_documents/chunking_report.md - Statistics and quality metrics
"""

import sys
import os
import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import tiktoken
from dotenv import load_dotenv
from scripts.logging_config import get_logger

logger = get_logger(__name__)

# Load environment variables
load_dotenv()

# Get project name
PROJECT_NAME = os.getenv("PRISM_PROJECT_NAME", "_example")

# LangChain text splitters
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter
)


# Token counting
def count_tokens(text: str, model: str = "cl100k_base") -> int:
    """Count tokens using tiktoken (same encoding as OpenAI embeddings)."""
    try:
        encoding = tiktoken.get_encoding(model)
        return len(encoding.encode(text))
    except Exception as e:
        # Fallback: rough estimate (1 token ≈ 4 characters)
        return len(text) // 4


def load_document_inventory() -> Dict:
    """Load document inventory from deduplication step, running it if needed."""
    inventory_path = Path("projects") / PROJECT_NAME / "output" / "document_inventory.json"

    if not inventory_path.exists():
        # Auto-run deduplication if inventory doesn't exist
        logger.info("Running deduplication (inventory not found)")
        from scripts.rag import deduplicate_documents
        result = deduplicate_documents.main()
        if result != 0:
            logger.error("Deduplication failed")
            return None
        # Check again after deduplication
        if not inventory_path.exists():
            logger.error("Deduplication completed but inventory not created")
            return None

    with open(inventory_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_page_numbers(markdown: str) -> List[int]:
    """
    Extract page numbers from markdown content.

    Looks for patterns like:
    - ## Page 1
    - ## Page 2
    - **Page Number:** 02/02
    """
    page_numbers = []

    # Pattern 1: ## Page N
    page_headers = re.findall(r'^##\s+Page\s+(\d+)', markdown, re.MULTILINE | re.IGNORECASE)
    page_numbers.extend([int(p) for p in page_headers])

    # Pattern 2: Page Number: N
    page_metadata = re.findall(r'\*\*Page Number\*\*:\s*(\d+)', markdown, re.IGNORECASE)
    page_numbers.extend([int(p) for p in page_metadata])

    # Pattern 3: Sheet No.: N/N
    sheet_metadata = re.findall(r'\*\*Sheet No\.\*\*:\s*(\d+)/', markdown, re.IGNORECASE)
    page_numbers.extend([int(p) for p in sheet_metadata])

    return sorted(set(page_numbers)) if page_numbers else [1]  # Default to page 1


def chunk_document(
    doc_path: str,
    content: str,
    content_hash: str,
    target_chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> List[Dict]:
    """
    Chunk a single document using semantic/structure-aware strategy.

    Args:
        doc_path: Path to the document
        content: Markdown content
        content_hash: Hash of the document
        target_chunk_size: Target tokens per chunk
        chunk_overlap: Overlap tokens between chunks

    Returns:
        List of chunk dictionaries with metadata
    """

    # Pre-process: Remove page marker headers (they're redundant metadata)
    # Pattern: "## Page N" on its own line
    content = re.sub(r'^##\s+Page\s+\d+\s*$', '', content, flags=re.MULTILINE | re.IGNORECASE)

    # Also remove common variations
    content = re.sub(r'^##\s+Page\s+\d+\s*/\s*\d+\s*$', '', content, flags=re.MULTILINE | re.IGNORECASE)

    # Clean up multiple blank lines
    content = re.sub(r'\n{3,}', '\n\n', content)

    # Step 1: Split by markdown headers (##, ###, etc.)
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
        ("####", "Header 4"),
    ]

    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False  # Keep headers in content for context
    )

    # Initial split by headers
    header_splits = markdown_splitter.split_text(content)

    # Step 2: Merge small adjacent sections to reach minimum viable chunk size
    # This prevents tiny chunks (< 400 tokens) that waste overlap budget
    min_chunk_size = 400
    merged_sections = []

    if header_splits:
        current_section = header_splits[0]
        current_tokens = count_tokens(current_section.page_content)

        for i in range(1, len(header_splits)):
            next_section = header_splits[i]
            next_tokens = count_tokens(next_section.page_content)

            # If current section is too small, merge with next
            if current_tokens < min_chunk_size:
                # Merge sections
                merged_content = current_section.page_content + "\n\n" + next_section.page_content

                # Combine metadata (keep both section titles if different)
                merged_metadata = current_section.metadata.copy()
                for key, value in next_section.metadata.items():
                    if key not in merged_metadata:
                        merged_metadata[key] = value
                    elif merged_metadata[key] != value:
                        # Different values - combine them
                        merged_metadata[key] = f"{merged_metadata[key]} / {value}"

                # Create merged section
                from langchain_core.documents import Document
                current_section = Document(page_content=merged_content, metadata=merged_metadata)
                current_tokens = count_tokens(merged_content)
            else:
                # Current section is large enough, save it and start new
                merged_sections.append(current_section)
                current_section = next_section
                current_tokens = next_tokens

        # Don't forget the last section
        merged_sections.append(current_section)

    # Step 3: Sub-chunk oversized sections
    # RecursiveCharacterTextSplitter for paragraph-level splitting
    # Use tiktoken to count actual tokens, not character approximation
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        token_counter = lambda text: len(encoding.encode(text))
    except Exception:
        # Fallback: rough estimate (1 token ≈ 4 characters)
        token_counter = lambda text: len(text) // 4

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=target_chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=token_counter,  # Count tokens, not characters
        separators=["\n\n", "\n", ". ", " ", ""],  # Paragraph -> sentence -> word
        is_separator_regex=False
    )

    # Process each merged section
    chunks = []
    chunk_index = 0

    for section in merged_sections:
        section_text = section.page_content
        section_metadata = section.metadata

        # Count tokens in section
        token_count = count_tokens(section_text)

        if token_count <= target_chunk_size:
            # Section is small enough, keep as single chunk
            chunks.append({
                'content': section_text,
                'token_count': token_count,
                'metadata': section_metadata,
                'chunk_index': chunk_index
            })
            chunk_index += 1
        else:
            # Section is too large, sub-chunk it
            sub_chunks = text_splitter.split_text(section_text)

            for sub_chunk in sub_chunks:
                chunks.append({
                    'content': sub_chunk,
                    'token_count': count_tokens(sub_chunk),
                    'metadata': section_metadata,
                    'chunk_index': chunk_index
                })
                chunk_index += 1

    # Step 3: Add document-level metadata
    source_file = Path(doc_path).stem.replace('_markdown', '')
    page_numbers = extract_page_numbers(content)

    final_chunks = []
    chunk_counter = 0

    for chunk in chunks:
        # Skip small chunks (< 200 tokens) - with 200 token overlap, these would be mostly redundant
        # Section merging should have already combined most small sections
        if chunk['token_count'] < 200:
            continue

        # Generate unique chunk ID
        chunk_id = f"{content_hash[:8]}_chunk_{chunk_counter:03d}"

        # Try to infer page number from content
        chunk_pages = extract_page_numbers(chunk['content'])
        page_number = chunk_pages[0] if chunk_pages else page_numbers[0]

        # Extract section title from metadata (if available)
        section_title = None
        if chunk['metadata']:
            # LangChain stores headers as metadata keys
            for header_type in ['Header 2', 'Header 3', 'Header 1', 'Header 4']:
                if header_type in chunk['metadata']:
                    section_title = chunk['metadata'][header_type]
                    break

        final_chunk = {
            'chunk_id': chunk_id,
            'content': chunk['content'],
            'source_file': source_file,
            'source_path': doc_path,
            'page_number': page_number,
            'chunk_index': chunk_counter,
            'total_chunks': len(chunks),  # Will be updated after filtering
            'token_count': chunk['token_count'],
            'document_hash': content_hash,
            'section_title': section_title
        }

        final_chunks.append(final_chunk)
        chunk_counter += 1

    # Update total_chunks count after filtering
    for chunk in final_chunks:
        chunk['total_chunks'] = len(final_chunks)

    return final_chunks


def generate_chunking_report(all_chunks: List[Dict], documents_processed: int) -> str:
    """Generate human-readable chunking report."""

    lines = [
        "# Document Chunking Report",
        "",
        f"**Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"**Documents Processed**: {documents_processed}",
        f"**Total Chunks**: {len(all_chunks)}",
        "",
        "---",
        ""
    ]

    # Statistics
    token_counts = [c['token_count'] for c in all_chunks]
    avg_tokens = sum(token_counts) / len(token_counts) if token_counts else 0
    min_tokens = min(token_counts) if token_counts else 0
    max_tokens = max(token_counts) if token_counts else 0

    lines.extend([
        "## Chunking Statistics",
        "",
        f"- **Average Chunk Size**: {avg_tokens:.0f} tokens",
        f"- **Min Chunk Size**: {min_tokens} tokens",
        f"- **Max Chunk Size**: {max_tokens} tokens",
        f"- **Target Size**: 1000 tokens",
        "",
        "---",
        ""
    ])

    # Per-document breakdown
    from collections import defaultdict
    chunks_per_doc = defaultdict(list)
    for chunk in all_chunks:
        chunks_per_doc[chunk['source_file']].append(chunk)

    lines.extend([
        "## Per-Document Breakdown",
        "",
        f"Chunked {len(chunks_per_doc)} unique documents:",
        ""
    ])

    for doc_name, doc_chunks in sorted(chunks_per_doc.items()):
        doc_tokens = [c['token_count'] for c in doc_chunks]
        lines.extend([
            f"### {doc_name}",
            f"- **Chunks**: {len(doc_chunks)}",
            f"- **Total Tokens**: {sum(doc_tokens):,}",
            f"- **Avg Chunk Size**: {sum(doc_tokens)/len(doc_chunks):.0f} tokens",
            ""
        ])

    # Quality checks
    oversized = [c for c in all_chunks if c['token_count'] > 1200]
    below_min = [c for c in all_chunks if c['token_count'] < 400]

    lines.extend([
        "---",
        "",
        "## Quality Checks",
        ""
    ])

    if oversized:
        lines.extend([
            f"⚠️ **Oversized Chunks** ({len(oversized)} chunks > 1200 tokens):",
            ""
        ])
        for chunk in oversized[:5]:  # Show first 5
            lines.append(f"- `{chunk['chunk_id']}`: {chunk['token_count']} tokens (from {chunk['source_file']})")
        if len(oversized) > 5:
            lines.append(f"- ... and {len(oversized) - 5} more")
        lines.append("")
    else:
        lines.extend([
            "✅ No oversized chunks (all <= 1200 tokens)",
            ""
        ])

    if below_min:
        lines.extend([
            f"ℹ️ **Below Target Minimum** ({len(below_min)} chunks < 400 tokens):",
            "- These passed 200-token filter but didn't reach merge target",
            "- May occur at document boundaries or for isolated short sections",
            ""
        ])
    else:
        lines.extend([
            "✅ All chunks meet minimum size (≥ 400 tokens)",
            ""
        ])

    lines.extend([
        "---",
        "",
        "## Next Steps",
        "",
        "1. Review chunk sizes and quality above",
        "2. Spot-check individual chunk files in chunked_documents/",
        "3. Run `python main.py embed` to generate embeddings",
        ""
    ])

    return "\n".join(lines)


def main():
    """Main entry point."""
    inventory = load_document_inventory()
    if not inventory:
        return 1

    documents = inventory['documents']
    logger.info(f"Chunking {len(documents)} documents")

    output_dir = Path("projects") / PROJECT_NAME / "output" / "chunked_documents"
    output_dir.mkdir(parents=True, exist_ok=True)

    all_chunks = []
    for i, doc in enumerate(documents, 1):
        try:
            content = Path(doc['path']).read_text(encoding='utf-8')
            chunks = chunk_document(
                doc_path=doc['path'],
                content=content,
                content_hash=doc['content_hash'],
                target_chunk_size=1000,
                chunk_overlap=200
            )
            for chunk in chunks:
                chunk_file = output_dir / f"{chunk['chunk_id']}.json"
                with open(chunk_file, 'w', encoding='utf-8') as f:
                    json.dump(chunk, f, indent=2, ensure_ascii=False)
            all_chunks.extend(chunks)
        except Exception as e:
            logger.error(f"Failed to chunk {doc['relative_path']}: {e}")

    # Generate report
    report = generate_chunking_report(all_chunks, len(documents))
    report_file = output_dir / "chunking_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    avg_tokens = sum(c['token_count'] for c in all_chunks) / len(all_chunks) if all_chunks else 0
    logger.info(f"Complete: {len(all_chunks)} chunks from {len(documents)} docs (avg {avg_tokens:.0f} tokens)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
