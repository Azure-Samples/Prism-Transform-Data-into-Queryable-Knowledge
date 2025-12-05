"""
Deduplicate extracted markdown documents.

Reads extraction results from blob storage, identifies duplicates,
saves inventory back to blob.

Usage:
    python main.py deduplicate --project myproject
"""

import sys
import os
import json
import hashlib
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Tuple
from dotenv import load_dotenv

from scripts.logging_config import get_logger
from apps.api.app.services.storage_service import get_storage_service

logger = get_logger(__name__)
load_dotenv()


def get_project_name() -> str:
    """Get project name at runtime (not import time)."""
    return os.getenv("PRISM_PROJECT_NAME", "_example")


def hash_content(content: str) -> str:
    """Generate SHA256 hash of markdown content."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def load_markdown_documents(storage) -> List[Dict]:
    """Load all markdown documents from blob storage."""
    project_name = get_project_name()
    files = storage.list_files(project_name, "output/extraction_results")

    if not files:
        logger.error("No extraction results found. Run extraction first.")
        return []

    markdown_files = [f for f in files if f["name"].endswith("_markdown.md")]
    logger.info(f"Found {len(markdown_files)} markdown files")

    documents = []
    for f in markdown_files:
        try:
            content_bytes = storage.read_file(project_name, f"output/extraction_results/{f['name']}")
            if not content_bytes:
                continue

            content = content_bytes.decode('utf-8')
            doc = {
                'path': f"output/extraction_results/{f['name']}",
                'relative_path': f['name'],
                'content': content,
                'content_hash': hash_content(content),
                'size_bytes': f['size'],
                'modified_datetime': f['modified'] or datetime.utcnow().isoformat()
            }
            documents.append(doc)

        except Exception as e:
            logger.warning(f"Could not load {f['name']}: {e}")

    return documents


def find_duplicates(documents: List[Dict]) -> Tuple[Dict, List]:
    """Group documents by content hash and select canonical version."""
    hash_groups = defaultdict(list)
    for doc in documents:
        hash_groups[doc['content_hash']].append(doc)

    selected_documents = []
    for content_hash, group in hash_groups.items():
        if len(group) == 1:
            selected_documents.append(group[0])
        else:
            # Multiple documents with same hash - select first (arbitrary)
            selected_documents.append(group[0])

    return dict(hash_groups), selected_documents


def generate_report(hash_groups: Dict, selected_documents: List[Dict], total_docs: int) -> str:
    """Generate deduplication report."""
    duplicate_groups = {h: g for h, g in hash_groups.items() if len(g) > 1}
    duplicate_count = sum(len(g) - 1 for g in duplicate_groups.values())

    lines = [
        "# Deduplication Report",
        "",
        f"**Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"**Total Documents**: {total_docs}",
        f"**Unique**: {len(hash_groups)}",
        f"**Duplicates Removed**: {duplicate_count}",
        ""
    ]

    if duplicate_groups:
        lines.append("## Duplicate Groups")
        for content_hash, group in duplicate_groups.items():
            lines.append(f"\n### Hash {content_hash[:16]}...")
            for doc in group:
                lines.append(f"- {doc['relative_path']}")

    return "\n".join(lines)


def main():
    """Main entry point."""
    storage = get_storage_service()

    documents = load_markdown_documents(storage)
    if not documents:
        logger.error("No documents found")
        return 1

    logger.info(f"Deduplicating {len(documents)} documents")

    hash_groups, selected_documents = find_duplicates(documents)
    duplicate_count = sum(len(g) - 1 for g in hash_groups.values() if len(g) > 1)

    # Save inventory to blob
    inventory = {
        "generated_at": datetime.utcnow().isoformat(),
        "total_documents": len(selected_documents),
        "documents": [
            {
                "content_hash": doc['content_hash'],
                "path": doc['path'],
                "relative_path": doc['relative_path'],
                "size_bytes": doc['size_bytes'],
                "modified_datetime": doc['modified_datetime'],
                "has_duplicates": len(hash_groups[doc['content_hash']]) > 1,
                "duplicate_count": len(hash_groups[doc['content_hash']]) - 1
            }
            for doc in selected_documents
        ]
    }
    project_name = get_project_name()
    storage.write_json(project_name, "output/document_inventory.json", inventory)

    # Save report
    report = generate_report(hash_groups, selected_documents, len(documents))
    storage.write_file(project_name, "output/deduplication_report.md", report.encode('utf-8'))

    logger.info(f"Complete: {len(selected_documents)} unique, {duplicate_count} duplicates removed")

    return 0


if __name__ == "__main__":
    sys.exit(main())
