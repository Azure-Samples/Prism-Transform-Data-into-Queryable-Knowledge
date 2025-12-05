"""
Generate embeddings for chunked documents using Azure OpenAI text-embedding-3-large.

Reads chunks from blob storage, generates embeddings, saves back to blob.

Uses 'enriched_content' (with document/section context) for embedding generation,
which improves retrieval by capturing both content AND context in the vector.

Usage:
    python main.py embed --project myproject
"""

import sys
import json
import time
import os
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv

from openai import AzureOpenAI
from scripts.logging_config import get_logger
from apps.api.app.services.storage_service import get_storage_service

logger = get_logger(__name__)
load_dotenv()


def get_project_name() -> str:
    """Get project name at runtime (not import time)."""
    return os.getenv("PRISM_PROJECT_NAME", "_example")


def load_chunk_files(storage) -> List[Dict]:
    """Load all chunks from blob storage."""
    project_name = get_project_name()
    files = storage.list_files(project_name, "output/chunked_documents")

    if not files:
        logger.error("No chunk files found. Run chunking first.")
        return []

    chunks = []
    for f in files:
        if not f["name"].endswith(".json"):
            continue
        content = storage.read_file(project_name, f"output/chunked_documents/{f['name']}")
        if content:
            try:
                chunks.append(json.loads(content.decode('utf-8')))
            except Exception as e:
                logger.warning(f"Could not load {f['name']}: {e}")

    return chunks


def get_embedded_chunk_ids(storage) -> set:
    """Get set of chunk IDs that already have embeddings."""
    files = storage.list_files(get_project_name(), "output/embedded_documents")
    return {f["name"].replace(".json", "") for f in files if f["name"].endswith(".json")}


def init_openai_client():
    """Initialize Azure OpenAI client."""
    api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")

    if not api_key or not endpoint:
        logger.error("Azure OpenAI credentials not found")
        return None

    return AzureOpenAI(api_key=api_key, azure_endpoint=endpoint, api_version=api_version)


def generate_embeddings_batch(
    client: AzureOpenAI,
    storage,
    chunks: List[Dict],
    deployment_name: str,
    dimensions: int = 1024,
    batch_size: int = 100,
    max_retries: int = 3
) -> Dict:
    """Generate embeddings and save to blob storage."""
    total = len(chunks)
    processed = 0
    failed = 0
    failed_chunks = []

    for i in range(0, total, batch_size):
        batch = chunks[i:i + batch_size]
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Use enriched_content (with document/section context) for better embeddings
                # Falls back to 'content' for backwards compatibility with old chunks
                texts = [chunk.get('enriched_content', chunk['content']) for chunk in batch]
                response = client.embeddings.create(
                    input=texts,
                    model=deployment_name,
                    dimensions=dimensions
                )

                for chunk, embedding_data in zip(batch, response.data):
                    chunk_with_embedding = chunk.copy()
                    chunk_with_embedding['embedding'] = embedding_data.embedding
                    chunk_with_embedding['embedding_model'] = deployment_name
                    chunk_with_embedding['embedding_dimensions'] = dimensions

                    # Save to blob
                    storage.write_json(
                        get_project_name(),
                        f"output/embedded_documents/{chunk['chunk_id']}.json",
                        chunk_with_embedding
                    )
                    processed += 1

                break  # Success

            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    logger.error(f"Batch failed after {max_retries} retries: {e}")
                    failed += len(batch)
                    failed_chunks.extend([c['chunk_id'] for c in batch])
                    break
                else:
                    wait_time = 2 ** retry_count
                    logger.warning(f"Retry {retry_count}/{max_retries}: {e}")
                    time.sleep(wait_time)

        time.sleep(0.5)  # Rate limit

    return {
        'total': total,
        'processed': processed,
        'failed': failed,
        'failed_chunks': failed_chunks
    }


def generate_report(stats: Dict, elapsed_time: float, skipped: int) -> str:
    """Generate embedding report."""
    deployment_name = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME", "text-embedding-3-large")
    dimensions = int(os.getenv("AZURE_OPENAI_EMBEDDING_DIMENSIONS", "1024"))

    lines = [
        "# Embedding Report",
        "",
        f"**Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"**Total Chunks**: {stats['total']}",
        f"**Skipped (already done)**: {skipped}",
        f"**Processed**: {stats['processed']}",
        f"**Failed**: {stats['failed']}",
        f"**Time**: {elapsed_time:.1f}s",
        "",
        f"**Model**: {deployment_name}",
        f"**Dimensions**: {dimensions}",
        ""
    ]

    if stats['failed'] > 0:
        lines.append("## Failed Chunks")
        for chunk_id in stats['failed_chunks'][:10]:
            lines.append(f"- {chunk_id}")
        lines.append("")

    return "\n".join(lines)


def main():
    """Main entry point."""
    storage = get_storage_service()
    deployment_name = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME", "text-embedding-3-large")
    dimensions = int(os.getenv("AZURE_OPENAI_EMBEDDING_DIMENSIONS", "1024"))

    client = init_openai_client()
    if not client:
        return 1

    chunks = load_chunk_files(storage)
    if not chunks:
        return 1

    # Resume capability
    embedded_ids = get_embedded_chunk_ids(storage)
    chunks_to_process = [c for c in chunks if c['chunk_id'] not in embedded_ids]
    skipped = len(embedded_ids)

    if not chunks_to_process:
        logger.info("All chunks already embedded")
        return 0

    logger.info(f"Embedding {len(chunks_to_process)} chunks ({skipped} already done)")

    start_time = time.time()
    stats = generate_embeddings_batch(
        client=client,
        storage=storage,
        chunks=chunks_to_process,
        deployment_name=deployment_name,
        dimensions=dimensions
    )
    elapsed_time = time.time() - start_time

    # Save report
    report = generate_report(stats, elapsed_time, skipped)
    storage.write_file(get_project_name(), "output/embedded_documents/embedding_report.md", report.encode('utf-8'))

    throughput = stats['processed'] / elapsed_time if elapsed_time > 0 else 0
    logger.info(f"Complete: {stats['processed']} embedded, {stats['failed']} failed ({elapsed_time:.1f}s, {throughput:.1f}/s)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
