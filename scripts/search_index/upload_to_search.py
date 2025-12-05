"""
Upload embedded chunks to Azure AI Search index.

This script loads chunks with embeddings and uploads them to the Azure AI Search
index for vector and hybrid search capabilities.

Upload Strategy:
    - Batch size: 1000 documents per batch
    - Automatic retry on transient failures
    - Progress tracking with verification

Usage:
    python scripts/upload_to_search.py

Output:
    - indexing_reports/upload_report.json - Upload statistics
    - indexing_reports/index_verification.md - Verification report
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.core.exceptions import HttpResponseError

from scripts.logging_config import get_logger

logger = get_logger(__name__)

# Load environment variables
load_dotenv()

from apps.api.app.services.storage_service import get_storage_service


def get_project_name() -> str:
    """Get project name at runtime (not import time)."""
    return os.getenv("PRISM_PROJECT_NAME", "_example")


def get_index_name() -> str:
    """
    Get index name from configuration.

    Priority:
    1. Derived from PRISM_PROJECT_NAME: prism-{project}-index (automatic)
    2. AZURE_SEARCH_INDEX_NAME env var (only if no project specified)
    3. Default: prism-default-index
    """
    project_name = get_project_name()
    if project_name:
        return f"prism-{project_name}-index"

    explicit_name = os.getenv("AZURE_SEARCH_INDEX_NAME")
    if explicit_name:
        return explicit_name

    return "prism-default-index"


def load_embedded_chunks() -> List[Dict]:
    """Load embedded chunks from blob storage."""
    storage = get_storage_service()
    project_name = get_project_name()

    files = storage.list_files(project_name, "output/embedded_documents")

    if not files:
        logger.error("No embedded chunk files found. Run embedding generation first.")
        return []

    chunks = []
    skipped = 0
    for f in files:
        if not f["name"].endswith(".json"):
            continue
        try:
            content = storage.read_file(project_name, f"output/embedded_documents/{f['name']}")
            if content:
                chunk = json.loads(content.decode('utf-8'))
                if 'embedding' in chunk:
                    chunks.append(chunk)
                else:
                    skipped += 1
        except Exception as e:
            logger.warning(f"Could not load {f['name']}: {e}")
            continue

    if skipped > 0:
        logger.warning(f"{skipped} chunks missing embedding field, skipped")

    return chunks


def get_search_client() -> SearchClient:
    """Initialize Azure AI Search client."""
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    admin_key = os.getenv("AZURE_SEARCH_ADMIN_KEY")
    index_name = get_index_name()

    if not endpoint or not admin_key:
        logger.error("Azure AI Search credentials not found in .env")
        return None

    credential = AzureKeyCredential(admin_key)
    client = SearchClient(endpoint=endpoint, index_name=index_name, credential=credential)

    return client


def transform_chunk_for_index(chunk: Dict) -> Dict:
    """
    Transform chunk to Azure AI Search document format.

    Uses 'enriched_content' (with document/section context) for the searchable content field.
    This improves both keyword and semantic search by including context in the indexed text.
    Falls back to 'content' for backwards compatibility with old chunks.

    Args:
        chunk: Chunk dictionary with embedding

    Returns:
        Document dictionary matching index schema
    """
    return {
        "chunk_id": chunk['chunk_id'],
        # Use enriched_content for search (includes document/section context)
        "content": chunk.get('enriched_content', chunk['content']),
        "content_vector": chunk['embedding'],
        "source_file": chunk['source_file'],
        "location": chunk['location'],
        "chunk_index": chunk['chunk_index']
    }


def upload_documents_batch(
    client: SearchClient,
    documents: List[Dict],
    batch_size: int = 1000,
    max_retries: int = 3
) -> Dict:
    """
    Upload documents in batches with retry logic.

    Args:
        client: Azure AI Search client
        documents: List of documents to upload
        batch_size: Number of documents per batch
        max_retries: Maximum retry attempts

    Returns:
        Dictionary with upload statistics
    """
    total = len(documents)
    uploaded_count = 0
    failed_count = 0
    failed_ids = []

    for i in range(0, total, batch_size):
        batch = documents[i:i + batch_size]

        retry_count = 0
        while retry_count < max_retries:
            try:
                result = client.upload_documents(documents=batch)
                succeeded = sum(1 for r in result if r.succeeded)
                failed = len(result) - succeeded

                uploaded_count += succeeded
                failed_count += failed

                if failed > 0:
                    failed_ids.extend([r.key for r in result if not r.succeeded])

                break

            except HttpResponseError as e:
                retry_count += 1
                if retry_count >= max_retries:
                    logger.error(f"Batch failed after {max_retries} retries: {e}")
                    failed_count += len(batch)
                    failed_ids.extend([doc['chunk_id'] for doc in batch])
                    break
                else:
                    wait_time = 2 ** retry_count
                    time.sleep(wait_time)

            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    logger.error(f"Batch failed after {max_retries} retries: {e}")
                    failed_count += len(batch)
                    failed_ids.extend([doc['chunk_id'] for doc in batch])
                    break
                else:
                    wait_time = 2 ** retry_count
                    time.sleep(wait_time)

        time.sleep(0.5)

    return {
        "total": total,
        "uploaded": uploaded_count,
        "failed": failed_count,
        "failed_ids": failed_ids
    }


def verify_index(client: SearchClient, expected_count: int) -> Dict:
    """
    Verify uploaded documents in index.

    Args:
        client: Azure AI Search client
        expected_count: Expected number of documents

    Returns:
        Dictionary with verification results
    """
    try:
        time.sleep(2)  # Brief wait for index to update
        results = client.search(search_text="*", include_total_count=True)
        actual_count = results.get_count()

        sample_results = client.search(
            search_text="voltage transformer",
            top=3,
            select=["chunk_id", "source_file", "location"]
        )
        sample_docs = list(sample_results)

        return {
            "expected_count": expected_count,
            "actual_count": actual_count,
            "match": actual_count == expected_count,
            "sample_query_results": len(sample_docs)
        }

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return {
            "expected_count": expected_count,
            "actual_count": None,
            "match": False,
            "error": str(e)
        }


def generate_upload_report(stats: Dict, verification: Dict, elapsed_time: float) -> str:
    """Generate human-readable upload report."""

    lines = [
        "# Document Upload Report",
        "",
        f"**Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"**Index**: {get_index_name()}",
        f"**Upload Time**: {elapsed_time:.1f} seconds ({elapsed_time/60:.1f} minutes)",
        "",
        "---",
        ""
    ]

    # Upload statistics
    success_rate = (stats['uploaded'] / stats['total'] * 100) if stats['total'] > 0 else 0

    lines.extend([
        "## Upload Statistics",
        "",
        f"- **Total Documents**: {stats['total']}",
        f"- **Uploaded Successfully**: {stats['uploaded']}",
        f"- **Failed**: {stats['failed']}",
        f"- **Success Rate**: {success_rate:.1f}%",
        f"- **Throughput**: {stats['uploaded']/elapsed_time:.1f} docs/second",
        "",
        "---",
        ""
    ])

    # Verification
    lines.extend([
        "## Index Verification",
        ""
    ])

    if verification['match']:
        lines.extend([
            f"✅ **Verification Passed**",
            f"- Expected: {verification['expected_count']} documents",
            f"- Found: {verification['actual_count']} documents",
            f"- Sample query returned {verification['sample_query_results']} results",
            ""
        ])
    else:
        lines.extend([
            f"⚠️ **Verification Issues**",
            f"- Expected: {verification['expected_count']} documents",
            f"- Found: {verification.get('actual_count', 'Unknown')} documents",
            ""
        ])

        if verification.get('error'):
            lines.append(f"- Error: {verification['error']}")
            lines.append("")

    # Failed documents
    if stats['failed'] > 0:
        lines.extend([
            "---",
            "",
            "## Failed Documents",
            "",
            f"{stats['failed']} documents failed to upload:",
            ""
        ])

        for chunk_id in stats['failed_ids'][:10]:  # Show first 10
            lines.append(f"- `{chunk_id}`")

        if len(stats['failed_ids']) > 10:
            lines.append(f"- ... and {len(stats['failed_ids']) - 10} more")

        lines.append("")

    lines.extend([
        "---",
        "",
        "## Next Steps",
        ""
    ])

    if stats['failed'] == 0 and verification['match']:
        lines.extend([
            "✅ **Upload Complete!** Index is ready for queries.",
            "",
            "Your knowledge store is now available for:",
            "- Vector search",
            "- Hybrid search (vector + keyword)",
            "- Semantic ranking",
            "- Agentic retrieval",
            ""
        ])
    else:
        lines.extend([
            "⚠️ **Action Required**:",
            ""
        ])

        if stats['failed'] > 0:
            lines.append("1. Review failed document IDs above")
            lines.append("2. Check for errors in upload logs")
            lines.append("3. Retry upload for failed documents")

        if not verification['match']:
            lines.append("1. Wait a few seconds and verify count again")
            lines.append("2. Check Azure AI Search portal for index status")

        lines.append("")

    return "\n".join(lines)


def main():
    """Main entry point."""
    index_name = get_index_name()

    client = get_search_client()
    if not client:
        return 1

    chunks = load_embedded_chunks()
    if not chunks:
        return 1

    logger.info(f"Uploading {len(chunks)} documents to index '{index_name}'")

    documents = [transform_chunk_for_index(chunk) for chunk in chunks]

    start_time = time.time()
    stats = upload_documents_batch(
        client=client,
        documents=documents,
        batch_size=1000,
        max_retries=3
    )
    elapsed_time = time.time() - start_time

    verification = verify_index(client, stats['uploaded'])

    # Save reports to blob storage
    storage = get_storage_service()
    project_name = get_project_name()

    storage.write_json(project_name, "output/upload_report.json", {
        'generated_at': datetime.utcnow().isoformat(),
        'index_name': index_name,
        'upload_stats': stats,
        'verification': verification,
        'elapsed_time': elapsed_time
    })

    report = generate_upload_report(stats, verification, elapsed_time)
    storage.write_file(project_name, "output/index_verification.md", report.encode('utf-8'))

    success_rate = (stats['uploaded'] / stats['total'] * 100) if stats['total'] > 0 else 0
    logger.info(f"Complete: {stats['uploaded']}/{stats['total']} uploaded ({success_rate:.0f}%), {elapsed_time:.1f}s")

    # Update project config to mark as indexed
    # Note: index_name is NOT stored in config - it's derived from project name
    if stats['uploaded'] > 0:
        config = storage.read_json(project_name, "config.json")
        if config:
            if 'status' not in config:
                config['status'] = {}
            config['status']['is_indexed'] = True
            # Remove index_name if it exists (we derive it from project name now)
            config['status'].pop('index_name', None)
            storage.write_json(project_name, "config.json", config)

    return 0


if __name__ == "__main__":
    sys.exit(main())
