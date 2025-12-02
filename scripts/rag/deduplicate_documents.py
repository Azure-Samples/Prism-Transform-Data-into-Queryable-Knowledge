"""
Deduplicate extracted markdown documents.

This script analyzes all extracted markdown files and identifies duplicates
based on content hashing. For near-identical documents, it selects the newest
version based on file modification time.

Usage:
    python main.py deduplicate --project myproject

Output:
    - projects/{project}/output/document_inventory.json - Tracks document hashes and selected files
    - projects/{project}/output/deduplication_report.md - Human-readable duplicate analysis
"""

import sys
import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Tuple
from dotenv import load_dotenv

from scripts.logging_config import get_logger
logger = get_logger(__name__)

# Load environment variables
load_dotenv()

# Get project name
PROJECT_NAME = os.getenv("PRISM_PROJECT_NAME", "_example")


def hash_content(content: str) -> str:
    """Generate SHA256 hash of markdown content."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def load_markdown_documents() -> List[Dict]:
    """
    Load all markdown documents from projects/{project}/output/extraction_results.

    Returns:
        List of document dictionaries with path, content, hash, mtime
    """
    extraction_dir = Path("projects") / PROJECT_NAME / "output" / "extraction_results"

    if not extraction_dir.exists():
        logger.error(f"{extraction_dir} not found. Run document extraction first.")
        return []

    documents = []
    markdown_files = list(extraction_dir.rglob("*_markdown.md"))

    logger.info(f"Found {len(markdown_files)} markdown files")

    for md_file in markdown_files:
        try:
            content = md_file.read_text(encoding='utf-8')
            file_stat = md_file.stat()

            doc = {
                'path': str(md_file),
                'relative_path': str(md_file.relative_to(extraction_dir)),
                'content': content,
                'content_hash': hash_content(content),
                'size_bytes': file_stat.st_size,
                'modified_time': file_stat.st_mtime,
                'modified_datetime': datetime.fromtimestamp(file_stat.st_mtime).isoformat()
            }
            documents.append(doc)

        except Exception as e:
            logger.warning(f"Could not load {md_file}: {e}")
            continue

    return documents


def find_duplicates(documents: List[Dict]) -> Tuple[Dict, List]:
    """
    Group documents by content hash and select canonical version.

    Args:
        documents: List of document dictionaries

    Returns:
        (hash_groups, selected_documents)
        - hash_groups: Dict mapping hash -> list of documents with that hash
        - selected_documents: List of selected canonical documents
    """
    # Group by hash
    hash_groups = defaultdict(list)
    for doc in documents:
        hash_groups[doc['content_hash']].append(doc)

    # Select canonical version for each group (newest file)
    selected_documents = []
    for content_hash, group in hash_groups.items():
        if len(group) == 1:
            # No duplicates
            selected_documents.append(group[0])
        else:
            # Multiple documents with same hash - select newest
            newest = max(group, key=lambda d: d['modified_time'])
            selected_documents.append(newest)

    return dict(hash_groups), selected_documents


def generate_report(hash_groups: Dict, selected_documents: List[Dict], total_docs: int) -> str:
    """Generate human-readable deduplication report."""

    lines = [
        "# Document Deduplication Report",
        "",
        f"**Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"**Total Documents Analyzed**: {total_docs}",
        "",
        "---",
        ""
    ]

    # Summary stats
    unique_count = len(hash_groups)
    duplicate_groups = {h: g for h, g in hash_groups.items() if len(g) > 1}
    duplicate_count = sum(len(g) - 1 for g in duplicate_groups.values())  # Extra copies

    lines.extend([
        "## Summary",
        "",
        f"- **Unique Documents**: {unique_count}",
        f"- **Duplicate Copies Found**: {duplicate_count}",
        f"- **Documents After Deduplication**: {len(selected_documents)}",
        f"- **Space Savings**: {duplicate_count} files can be ignored",
        "",
        "---",
        ""
    ])

    if not duplicate_groups:
        lines.extend([
            "## Result",
            "",
            "✅ No duplicates found! All documents are unique.",
            ""
        ])
    else:
        lines.extend([
            "## Duplicate Groups",
            "",
            f"Found {len(duplicate_groups)} groups of duplicate documents:",
            ""
        ])

        for i, (content_hash, group) in enumerate(duplicate_groups.items(), 1):
            # Sort by modification time
            sorted_group = sorted(group, key=lambda d: d['modified_time'], reverse=True)
            newest = sorted_group[0]

            lines.extend([
                f"### Group {i} ({len(group)} copies)",
                "",
                f"**Content Hash**: `{content_hash[:16]}...`",
                f"**File Size**: {newest['size_bytes']:,} bytes",
                "",
                "**Selected (newest)**:",
                f"- `{newest['relative_path']}`",
                f"  - Modified: {newest['modified_datetime']}",
                "",
                "**Duplicates (older)**:",
            ])

            for doc in sorted_group[1:]:
                lines.extend([
                    f"- `{doc['relative_path']}`",
                    f"  - Modified: {doc['modified_datetime']}",
                ])

            lines.append("")

    lines.extend([
        "---",
        "",
        "## Next Steps",
        "",
        "1. Review duplicate groups above",
        "2. Selected documents will be used for chunking",
        "3. Older duplicates will be ignored in the RAG pipeline",
        "4. Run `python main.py chunk` to proceed with chunking",
        ""
    ])

    return "\n".join(lines)


def save_inventory(selected_documents: List[Dict], hash_groups: Dict):
    """Save document inventory for downstream processing."""

    # Create output directory if it doesn't exist
    data_dir = Path("projects") / PROJECT_NAME / "output"
    data_dir.mkdir(parents=True, exist_ok=True)

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
                "duplicate_count": len(hash_groups[doc['content_hash']]) - 1,
                "duplicate_paths": [
                    d['relative_path'] for d in hash_groups[doc['content_hash']]
                    if d['path'] != doc['path']
                ]
            }
            for doc in selected_documents
        ]
    }

    inventory_path = data_dir / "document_inventory.json"
    with open(inventory_path, 'w', encoding='utf-8') as f:
        json.dump(inventory, f, indent=2, ensure_ascii=False)

    return inventory_path


def main():
    """Main entry point."""
    documents = load_markdown_documents()
    if not documents:
        logger.error("No documents found to analyze")
        return 1

    logger.info(f"Deduplicating {len(documents)} documents")

    hash_groups, selected_documents = find_duplicates(documents)
    duplicate_count = sum(len(g) - 1 for g in hash_groups.values() if len(g) > 1)

    # Generate report
    report = generate_report(hash_groups, selected_documents, len(documents))
    data_dir = Path("projects") / PROJECT_NAME / "output"
    data_dir.mkdir(parents=True, exist_ok=True)
    report_path = data_dir / "deduplication_report.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    save_inventory(selected_documents, hash_groups)

    logger.info(f"Complete: {len(selected_documents)} unique, {duplicate_count} duplicates removed")

    return 0


if __name__ == "__main__":
    sys.exit(main())
