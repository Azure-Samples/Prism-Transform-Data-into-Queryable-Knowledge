"""
Chunk deduplicated markdown documents using semantic/structure-aware strategies.

Reads from blob storage, chunks documents, saves back to blob.

Usage:
    python main.py chunk --project myproject
"""

import sys
import os
import json
import re
from datetime import datetime
from typing import List, Dict
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


def extract_page_numbers(markdown: str) -> List[int]:
    """Extract page numbers from markdown content."""
    page_numbers = []
    page_headers = re.findall(r'^##\s+Page\s+(\d+)', markdown, re.MULTILINE | re.IGNORECASE)
    page_numbers.extend([int(p) for p in page_headers])
    page_metadata = re.findall(r'\*\*Page Number\*\*:\s*(\d+)', markdown, re.IGNORECASE)
    page_numbers.extend([int(p) for p in page_metadata])
    return sorted(set(page_numbers)) if page_numbers else [1]


def chunk_document(
    doc_path: str,
    content: str,
    content_hash: str,
    target_chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> List[Dict]:
    """Chunk a single document."""

    # Pre-process: Remove page marker headers
    content = re.sub(r'^##\s+Page\s+\d+\s*$', '', content, flags=re.MULTILINE | re.IGNORECASE)
    content = re.sub(r'^##\s+Page\s+\d+\s*/\s*\d+\s*$', '', content, flags=re.MULTILINE | re.IGNORECASE)
    content = re.sub(r'\n{3,}', '\n\n', content)

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
    header_splits = markdown_splitter.split_text(content)

    # Merge small adjacent sections
    min_chunk_size = 400
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
    chunk_index = 0

    for section in merged_sections:
        section_text = section.page_content
        section_metadata = section.metadata
        token_count = count_tokens(section_text)

        if token_count <= target_chunk_size:
            chunks.append({
                'content': section_text,
                'token_count': token_count,
                'metadata': section_metadata,
                'chunk_index': chunk_index
            })
            chunk_index += 1
        else:
            sub_chunks = text_splitter.split_text(section_text)
            for sub_chunk in sub_chunks:
                chunks.append({
                    'content': sub_chunk,
                    'token_count': count_tokens(sub_chunk),
                    'metadata': section_metadata,
                    'chunk_index': chunk_index
                })
                chunk_index += 1

    # Add document-level metadata
    source_file = doc_path.replace('_markdown.md', '').replace('output/extraction_results/', '')
    page_numbers = extract_page_numbers(content)

    final_chunks = []
    chunk_counter = 0

    for chunk in chunks:
        if chunk['token_count'] < 200:
            continue

        chunk_id = f"{content_hash[:8]}_chunk_{chunk_counter:03d}"
        chunk_pages = extract_page_numbers(chunk['content'])
        page_number = chunk_pages[0] if chunk_pages else page_numbers[0]

        section_title = None
        if chunk['metadata']:
            for header_type in ['Header 2', 'Header 3', 'Header 1', 'Header 4']:
                if header_type in chunk['metadata']:
                    section_title = chunk['metadata'][header_type]
                    break

        final_chunks.append({
            'chunk_id': chunk_id,
            'content': chunk['content'],
            'source_file': source_file,
            'source_path': doc_path,
            'page_number': page_number,
            'chunk_index': chunk_counter,
            'total_chunks': len(chunks),
            'token_count': chunk['token_count'],
            'document_hash': content_hash,
            'section_title': section_title
        })
        chunk_counter += 1

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
        lines.extend([
            f"**Avg Size**: {sum(token_counts)/len(token_counts):.0f} tokens",
            f"**Min/Max**: {min(token_counts)}/{max(token_counts)} tokens",
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
            # Read content from blob - path is relative like "output/extraction_results/file_markdown.md"
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
