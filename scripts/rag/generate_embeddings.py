"""
Generate embeddings for chunked documents using Azure OpenAI text-embedding-3-large.

This script loads individual chunk files, generates vector embeddings,
and saves embedded chunks as individual files. Supports resume on interruption.

Configuration:
    - Model: text-embedding-3-large
    - Dimensions: 1024
    - Batch size: 100 chunks per batch
    - Rate limiting: Exponential backoff on errors
    - Resume: Skips already-embedded chunks

Usage:
    python main.py embed --project myproject

Output:
    - projects/{project}/output/embedded_documents/{chunk_id}.json - Individual embedded chunks
    - projects/{project}/output/embedded_documents/embedding_report.md - Statistics and quality metrics
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv
import os

from openai import AzureOpenAI
from scripts.logging_config import get_logger

logger = get_logger(__name__)


# Load environment variables
load_dotenv()

# Get project name
PROJECT_NAME = os.getenv("PRISM_PROJECT_NAME", "_example")


def load_chunk_files() -> List[Dict]:
    """Load all chunk files from projects/{project}/output/chunked_documents directory."""
    chunks_dir = Path("projects") / PROJECT_NAME / "output" / "chunked_documents"

    if not chunks_dir.exists():
        logger.error(f"{chunks_dir} not found. Run chunking first.")
        return []

    chunk_files = list(chunks_dir.glob("*.json"))

    if not chunk_files:
        logger.error(f"No chunk files found in {chunks_dir}")
        return []

    chunks = []
    for chunk_file in chunk_files:
        try:
            with open(chunk_file, 'r', encoding='utf-8') as f:
                chunk = json.load(f)
                chunks.append(chunk)
        except Exception as e:
            logger.warning(f"Could not load {chunk_file}: {e}")
            continue

    return chunks


def get_embedded_chunk_ids() -> set:
    """Get set of chunk IDs that already have embeddings."""
    embedded_dir = Path("projects") / PROJECT_NAME / "output" / "embedded_documents"

    if not embedded_dir.exists():
        return set()

    embedded_files = list(embedded_dir.glob("*.json"))
    return {f.stem for f in embedded_files}


def init_openai_client():
    """Initialize Azure OpenAI client."""
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")

    if not api_key or not endpoint:
        logger.error("Azure OpenAI credentials not found in .env")
        logger.error("Required: AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT")
        return None

    client = AzureOpenAI(
        api_key=api_key,
        azure_endpoint=endpoint,
        api_version=api_version
    )

    return client


def generate_embeddings_batch(
    client: AzureOpenAI,
    chunks: List[Dict],
    deployment_name: str,
    dimensions: int = 1024,
    batch_size: int = 100,
    max_retries: int = 3,
    output_dir: Path = None
) -> Dict:
    """
    Generate embeddings for chunks in batches and save immediately.

    Args:
        client: Azure OpenAI client
        chunks: List of chunk dictionaries
        deployment_name: Deployment name for embedding model
        dimensions: Embedding dimensions
        batch_size: Number of chunks per batch
        max_retries: Maximum retry attempts on failure
        output_dir: Directory to save embedded chunks

    Returns:
        Statistics dictionary
    """
    total = len(chunks)
    processed = 0
    failed = 0
    failed_chunks = []

    for i in range(0, total, batch_size):
        batch = chunks[i:i + batch_size]

        retry_count = 0
        while retry_count < max_retries:
            try:
                texts = [chunk['content'] for chunk in batch]
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

                    chunk_file = output_dir / f"{chunk['chunk_id']}.json"
                    with open(chunk_file, 'w', encoding='utf-8') as f:
                        json.dump(chunk_with_embedding, f, indent=2, ensure_ascii=False)

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

        # Brief pause between batches to respect rate limits
        time.sleep(0.5)

    return {
        'total': total,
        'processed': processed,
        'failed': failed,
        'failed_chunks': failed_chunks
    }


def generate_embedding_report(stats: Dict, elapsed_time: float, skipped: int) -> str:
    """Generate human-readable embedding report."""

    deployment_name = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME", "text-embedding-3-large")
    dimensions = int(os.getenv("AZURE_OPENAI_EMBEDDING_DIMENSIONS", "1024"))

    lines = [
        "# Embedding Generation Report",
        "",
        f"**Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"**Total Chunks**: {stats['total']}",
        f"**Already Embedded (skipped)**: {skipped}",
        f"**Newly Processed**: {stats['processed']}",
        f"**Failed**: {stats['failed']}",
        f"**Processing Time**: {elapsed_time:.1f} seconds ({elapsed_time/60:.1f} minutes)",
        "",
        "---",
        ""
    ]

    # Configuration
    lines.extend([
        "## Embedding Configuration",
        "",
        f"- **Model**: {deployment_name}",
        f"- **Dimensions**: {dimensions}",
        f"- **Batch Size**: 100 chunks",
        "",
        "---",
        ""
    ])

    # Statistics
    if stats['processed'] > 0:
        success_rate = (stats['processed'] / (stats['processed'] + stats['failed']) * 100)
        avg_time_per_chunk = elapsed_time / stats['processed']
        throughput = stats['processed'] / elapsed_time

        lines.extend([
            "## Processing Statistics",
            "",
            f"- **Success Rate**: {success_rate:.1f}%",
            f"- **Avg Time per Chunk**: {avg_time_per_chunk:.3f} seconds",
            f"- **Throughput**: {throughput:.1f} chunks/second",
            "",
            "---",
            ""
        ])

    # Resume capability
    if skipped > 0:
        lines.extend([
            "## Resume Capability",
            "",
            f"✅ **Resumed from previous run**",
            f"- Skipped {skipped} already-embedded chunks",
            f"- Only processed new chunks",
            "",
            "---",
            ""
        ])

    # Failed chunks
    if stats['failed'] > 0:
        lines.extend([
            "## Failed Chunks",
            "",
            f"⚠️ {stats['failed']} chunks failed to embed:",
            ""
        ])
        for chunk_id in stats['failed_chunks'][:10]:
            lines.append(f"- `{chunk_id}`")
        if len(stats['failed_chunks']) > 10:
            lines.append(f"- ... and {len(stats['failed_chunks']) - 10} more")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## Next Steps",
        "",
        "1. Review embedding statistics above",
        "2. Check embedded_documents/ directory for individual files",
        "3. Run `python main.py index create` to create Azure AI Search index",
        "4. Run `python main.py index upload` to upload embedded chunks",
        ""
    ])

    return "\n".join(lines)


def main():
    """Main entry point."""
    deployment_name = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME", "text-embedding-3-large")
    dimensions = int(os.getenv("AZURE_OPENAI_EMBEDDING_DIMENSIONS", "1024"))

    client = init_openai_client()
    if not client:
        return 1

    output_dir = Path("projects") / PROJECT_NAME / "output" / "embedded_documents"
    output_dir.mkdir(parents=True, exist_ok=True)

    chunks = load_chunk_files()
    if not chunks:
        return 1

    # Check for already-embedded (resume capability)
    embedded_ids = get_embedded_chunk_ids()
    chunks_to_process = [c for c in chunks if c['chunk_id'] not in embedded_ids]
    skipped = len(embedded_ids)

    if not chunks_to_process:
        logger.info("All chunks already embedded")
        return 0

    logger.info(f"Embedding {len(chunks_to_process)} chunks ({skipped} already done)")

    start_time = time.time()
    try:
        stats = generate_embeddings_batch(
            client=client,
            chunks=chunks_to_process,
            deployment_name=deployment_name,
            dimensions=dimensions,
            batch_size=100,
            max_retries=3,
            output_dir=output_dir
        )
    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        return 1

    elapsed_time = time.time() - start_time

    # Generate report
    report = generate_embedding_report(stats, elapsed_time, skipped)
    report_file = output_dir / "embedding_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    throughput = stats['processed'] / elapsed_time if elapsed_time > 0 else 0
    logger.info(f"Complete: {stats['processed']} embedded, {stats['failed']} failed ({elapsed_time:.1f}s, {throughput:.1f}/s)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
