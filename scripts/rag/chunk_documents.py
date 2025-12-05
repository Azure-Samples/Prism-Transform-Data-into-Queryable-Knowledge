"""
Chunk deduplicated markdown documents using semantic/structure-aware strategies.

Reads from blob storage, chunks documents, saves back to blob.

Features:
- Page-aware chunking (splits by page first, then by headers/size)
- Contextual chunk enrichment (prepends document/section/page context for better embeddings)
- Token-based sizing with tiktoken

Usage:
    python main.py chunk --project myproject
"""

import sys
import os
import re
from datetime import datetime
from typing import List, Dict, Tuple
import tiktoken
from dotenv import load_dotenv

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from scripts.logging_config import get_logger
from apps.api.app.services.storage_service import get_storage_service

logger = get_logger(__name__)
load_dotenv()


def get_project_name() -> str:
    """Get project name at runtime (not import time)."""
    return os.getenv("PRISM_PROJECT_NAME", "_example")


def count_tokens(text: str, model: str = "cl100k_base") -> int:
    """Count tokens using tiktoken."""
    try:
        encoding = tiktoken.get_encoding(model)
        return len(encoding.encode(text))
    except Exception:
        return len(text) // 4


def load_document_inventory(storage) -> Dict:
    """Load document inventory from blob storage."""
    project_name = get_project_name()
    inventory = storage.read_json(project_name, "output/document_inventory.json")

    if not inventory:
        # Auto-run deduplication
        logger.info("Running deduplication (inventory not found)")
        from scripts.rag import deduplicate_documents
        result = deduplicate_documents.main()
        if result != 0:
            logger.error("Deduplication failed")
            return None
        inventory = storage.read_json(project_name, "output/document_inventory.json")

    return inventory


def split_by_pages(content: str) -> List[Tuple[int, str]]:
    """
    Split markdown content by page markers.

    Looks for "## Page N" markers and splits content into (page_number, content) tuples.
    Works with existing extractions that have page markers embedded.

    Args:
        content: Raw markdown with "## Page N" markers

    Returns:
        List of (page_number, page_content) tuples
    """
    # Pattern matches "## Page 1", "## Page 123", etc.
    page_pattern = r'^##\s+Page\s+(\d+)\s*$'

    # Find all page markers with their positions
    markers = list(re.finditer(page_pattern, content, re.MULTILINE | re.IGNORECASE))

    if not markers:
        # No page markers - treat as single page
        return [(1, content)]

    pages = []
    for i, match in enumerate(markers):
        page_num = int(match.group(1))
        start = match.end()  # Start after the marker

        # End is either next marker or end of content
        if i + 1 < len(markers):
            end = markers[i + 1].start()
        else:
            end = len(content)

        page_content = content[start:end].strip()

        # Remove leading/trailing separators (---)
        page_content = re.sub(r'^---\s*', '', page_content)
        page_content = re.sub(r'\s*---\s*$', '', page_content)

        if page_content:  # Only add non-empty pages
            pages.append((page_num, page_content))

    return pages


def clean_section_title(title: str) -> str:
    """Remove markdown formatting from section titles for cleaner context."""
    if not title:
        return title
    # Remove bold markers
    title = title.replace('**', '')
    # Remove italic markers
    title = title.replace('*', '')
    # Clean up extra whitespace
    title = ' '.join(title.split())
    return title.strip()


def build_context_prefix(source_file: str, section_hierarchy: Dict, page_number: int) -> str:
    """
    Build a context prefix to prepend to chunk content for better embeddings.

    This implements "Contextual Chunk Enrichment" - by including document and section
    context in the chunk, the embedding captures both WHAT the content says and
    WHERE it comes from, dramatically improving retrieval accuracy.
    """
    parts = []

    # Document name (clean up the filename)
    doc_name = source_file.replace('_', ' ').replace('.pdf', '').replace('.xlsx', '').replace('.msg', '')
    parts.append(f"Document: {doc_name}")

    # Build section hierarchy
    section_parts = []
    for header_level in ['Header 1', 'Header 2', 'Header 3', 'Header 4']:
        if header_level in section_hierarchy and section_hierarchy[header_level]:
            clean_title = clean_section_title(section_hierarchy[header_level])
            if clean_title:
                section_parts.append(clean_title)

    if section_parts:
        parts.append(f"Section: {' > '.join(section_parts)}")

    # Page reference
    if page_number:
        parts.append(f"Page: {page_number}")

    return "\n".join(parts) + "\n\n"


def chunk_page_content(
    page_content: str,
    page_number: int,
    target_chunk_size: int = 1000,
    chunk_overlap: int = 200,
    min_chunk_size: int = 400
) -> List[Dict]:
    """
    Chunk a single page's content using markdown headers and token limits.

    Args:
        page_content: Markdown content for one page
        page_number: The page number (for metadata)
        target_chunk_size: Target tokens per chunk
        chunk_overlap: Token overlap between chunks
        min_chunk_size: Minimum tokens to keep a chunk

    Returns:
        List of chunk dicts with content, metadata, page_number
    """
    # Clean up content
    page_content = re.sub(r'\n{3,}', '\n\n', page_content)

    if not page_content.strip():
        return []

    # Split by markdown headers
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
        ("####", "Header 4"),
    ]

    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False
    )

    try:
        header_splits = markdown_splitter.split_text(page_content)
    except Exception:
        # Fallback if header splitting fails
        header_splits = [Document(page_content=page_content, metadata={})]

    # Merge small adjacent sections
    merged_sections = []

    if header_splits:
        current_section = header_splits[0]
        current_tokens = count_tokens(current_section.page_content)

        for i in range(1, len(header_splits)):
            next_section = header_splits[i]
            next_tokens = count_tokens(next_section.page_content)

            if current_tokens < min_chunk_size:
                merged_content = current_section.page_content + "\n\n" + next_section.page_content
                merged_metadata = current_section.metadata.copy()
                for key, value in next_section.metadata.items():
                    if key not in merged_metadata:
                        merged_metadata[key] = value
                    elif merged_metadata[key] != value:
                        merged_metadata[key] = f"{merged_metadata[key]} / {value}"
                current_section = Document(page_content=merged_content, metadata=merged_metadata)
                current_tokens = count_tokens(merged_content)
            else:
                merged_sections.append(current_section)
                current_section = next_section
                current_tokens = next_tokens

        merged_sections.append(current_section)

    # Sub-chunk oversized sections
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        token_counter = lambda text: len(encoding.encode(text))
    except Exception:
        token_counter = lambda text: len(text) // 4

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=target_chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=token_counter,
        separators=["\n\n", "\n", ". ", " ", ""],
        is_separator_regex=False
    )

    chunks = []
    for section in merged_sections:
        section_text = section.page_content
        section_metadata = section.metadata
        token_count = count_tokens(section_text)

        if token_count <= target_chunk_size:
            chunks.append({
                'content': section_text,
                'token_count': token_count,
                'metadata': section_metadata,
                'page_number': page_number
            })
        else:
            sub_chunks = text_splitter.split_text(section_text)
            for sub_chunk in sub_chunks:
                chunks.append({
                    'content': sub_chunk,
                    'token_count': count_tokens(sub_chunk),
                    'metadata': section_metadata,
                    'page_number': page_number
                })

    return chunks


def chunk_document(
    doc_path: str,
    content: str,
    content_hash: str,
    target_chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> List[Dict]:
    """
    Chunk a document with page-aware splitting.

    Strategy:
    1. Split content by page markers ("## Page N")
    2. Chunk each page independently
    3. Each chunk knows its exact page number
    """
    source_file = doc_path.replace('_markdown.md', '').replace('output/extraction_results/', '')

    # Step 1: Split by pages
    pages = split_by_pages(content)
    logger.debug(f"Document has {len(pages)} pages")

    # Step 2: Chunk each page
    all_chunks = []
    for page_number, page_content in pages:
        page_chunks = chunk_page_content(
            page_content=page_content,
            page_number=page_number,
            target_chunk_size=target_chunk_size,
            chunk_overlap=chunk_overlap
        )
        all_chunks.extend(page_chunks)

    # Step 3: Build final chunks with IDs and enriched content
    final_chunks = []
    chunk_counter = 0

    for chunk in all_chunks:
        # Skip very small chunks
        if chunk['token_count'] < 200:
            continue

        chunk_id = f"{content_hash[:8]}_chunk_{chunk_counter:03d}"
        page_number = chunk['page_number']
        section_hierarchy = chunk['metadata'] if chunk['metadata'] else {}

        # Get section title
        section_title = None
        if section_hierarchy:
            for header_type in ['Header 2', 'Header 3', 'Header 1', 'Header 4']:
                if header_type in section_hierarchy:
                    section_title = section_hierarchy[header_type]
                    break

        # Build enriched content with context
        context_prefix = build_context_prefix(source_file, section_hierarchy, page_number)
        enriched_content = context_prefix + chunk['content']
        enriched_token_count = count_tokens(enriched_content)

        final_chunks.append({
            'chunk_id': chunk_id,
            'content': chunk['content'],
            'enriched_content': enriched_content,
            'source_file': source_file,
            'source_path': doc_path,
            'page_number': page_number,
            'chunk_index': chunk_counter,
            'total_chunks': 0,  # Updated below
            'token_count': chunk['token_count'],
            'enriched_token_count': enriched_token_count,
            'document_hash': content_hash,
            'section_title': section_title,
            'section_hierarchy': section_hierarchy
        })
        chunk_counter += 1

    # Update total_chunks
    for chunk in final_chunks:
        chunk['total_chunks'] = len(final_chunks)

    return final_chunks


def generate_report(all_chunks: List[Dict], documents_processed: int) -> str:
    """Generate chunking report."""
    lines = [
        "# Chunking Report",
        "",
        f"**Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"**Documents**: {documents_processed}",
        f"**Chunks**: {len(all_chunks)}",
        ""
    ]

    if all_chunks:
        token_counts = [c['token_count'] for c in all_chunks]
        page_numbers = [c['page_number'] for c in all_chunks]
        lines.extend([
            f"**Avg Size**: {sum(token_counts)/len(token_counts):.0f} tokens",
            f"**Min/Max**: {min(token_counts)}/{max(token_counts)} tokens",
            f"**Page Range**: {min(page_numbers)} - {max(page_numbers)}",
            ""
        ])

    return "\n".join(lines)


def main():
    """Main entry point."""
    storage = get_storage_service()

    inventory = load_document_inventory(storage)
    if not inventory:
        return 1

    documents = inventory['documents']
    logger.info(f"Chunking {len(documents)} documents")

    all_chunks = []
    for doc in documents:
        try:
            content_bytes = storage.read_file(get_project_name(), doc['path'])
            if not content_bytes:
                logger.warning(f"Could not read {doc['path']}")
                continue

            content = content_bytes.decode('utf-8')

            chunks = chunk_document(
                doc_path=doc['path'],
                content=content,
                content_hash=doc['content_hash'],
                target_chunk_size=1000,
                chunk_overlap=200
            )

            # Save each chunk to blob
            project_name = get_project_name()
            for chunk in chunks:
                storage.write_json(
                    project_name,
                    f"output/chunked_documents/{chunk['chunk_id']}.json",
                    chunk
                )

            all_chunks.extend(chunks)

        except Exception as e:
            logger.error(f"Failed to chunk {doc.get('relative_path', doc.get('path'))}: {e}")

    # Save report
    report = generate_report(all_chunks, len(documents))
    storage.write_file(get_project_name(), "output/chunked_documents/chunking_report.md", report.encode('utf-8'))

    avg_tokens = sum(c['token_count'] for c in all_chunks) / len(all_chunks) if all_chunks else 0
    logger.info(f"Complete: {len(all_chunks)} chunks from {len(documents)} docs (avg {avg_tokens:.0f} tokens)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
