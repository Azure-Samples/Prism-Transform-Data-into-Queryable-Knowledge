"""
Process all documents using Agent Framework with intelligent routing.

Reads documents from blob storage, processes with appropriate extractors,
saves results back to blob.

Usage:
    python main.py process --project myproject
"""

import os
import sys
import json
import time
import tempfile
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, List

from scripts.extraction.pdf_extraction_hybrid import process_pdf_hybrid_sync
from scripts.extraction.excel_extraction_agents import process_excel_with_agents_sync
from scripts.extraction.email_extraction_agents import process_email_with_agents_sync
from scripts.logging_config import get_logger
from apps.api.app.services.storage_service import get_storage_service

logger = get_logger(__name__)

try:
    from apps.api.app.services.progress_tracker import report_progress, set_document_context
except ImportError:
    def report_progress(current: int, total: int, message: str = "") -> None:
        pass
    def set_document_context(doc_num: int, total_docs: int, doc_name: str = "") -> None:
        pass

load_dotenv()


def get_project_name() -> str:
    """Get project name at runtime (not import time)."""
    return os.getenv("PRISM_PROJECT_NAME", "_example")


def list_all_documents(storage) -> List[Dict]:
    """Get all documents to process from blob storage."""
    project_name = get_project_name()
    files = storage.list_files(project_name, "documents")

    if not files:
        logger.error("No documents found")
        return []

    # Only process supported formats
    supported = [".pdf", ".xlsx", ".xlsm", ".msg"]
    documents = []
    for f in files:
        ext = Path(f["name"]).suffix.lower()
        if ext in supported:
            documents.append(f)

    return sorted(documents, key=lambda x: x["name"])


def load_extraction_status(storage) -> Dict:
    """Load extraction status from blob."""
    status = storage.read_json(get_project_name(), "output/extraction_status.json")
    return status if status else {"documents": {}}


def save_extraction_status(storage, status: Dict) -> None:
    """Save extraction status to blob."""
    storage.write_json(get_project_name(), "output/extraction_status.json", status)


def get_document_status(status: Dict, filename: str) -> str:
    """Get extraction status for a document."""
    return status.get("documents", {}).get(filename, {}).get("status", "pending")


def update_document_status(status: Dict, filename: str, doc_status: str, **kwargs) -> None:
    """Update extraction status for a document."""
    if "documents" not in status:
        status["documents"] = {}
    status["documents"][filename] = {
        "status": doc_status,
        "updated_at": datetime.utcnow().isoformat(),
        **kwargs
    }


def calculate_quality_metrics(result: dict, markdown: str) -> Dict:
    """Calculate quality metrics for extraction."""
    metrics = {
        "success": True,
        "markdown_length": len(markdown),
        "word_count": len(markdown.split()),
        "has_tables": "|" in markdown and markdown.count("|") > 10,
    }

    score = 0
    if metrics["word_count"] > 0:
        score += 30
    if metrics["word_count"] > 500:
        score += 30
    if metrics["has_tables"]:
        score += 20
    if len(markdown) > 1000:
        score += 20

    metrics["quality_score"] = min(score, 100)
    return metrics


def process_document(storage, doc: Dict, temp_dir: Path) -> Dict:
    """
    Process a single document.
    Downloads from blob, extracts, uploads result.
    """
    filename = doc["name"]
    ext = Path(filename).suffix.lower()

    # Download file to temp
    content = storage.read_file(get_project_name(), f"documents/{filename}")
    if not content:
        return None

    temp_file = temp_dir / filename
    temp_file.write_bytes(content)

    # Route by file type
    result = None
    if ext == ".pdf":
        result = process_pdf_hybrid_sync(temp_file)
    elif ext in ['.xlsx', '.xlsm']:
        result = process_excel_with_agents_sync(temp_file)
    elif ext == ".msg":
        result = process_email_with_agents_sync(temp_file)

    # Clean up temp file
    temp_file.unlink()

    return result


def save_extraction(storage, filename: str, result: dict) -> Dict:
    """Save extraction results to blob."""
    base_name = Path(filename).stem

    extraction_meta = {
        "file_name": filename,
        "processed_at": datetime.utcnow().isoformat(),
    }

    # Save raw JSON
    project_name = get_project_name()
    storage.write_json(
        project_name,
        f"output/extraction_results/{base_name}_raw.json",
        result
    )

    # Extract and save markdown
    markdown = ""
    if "result" in result and "contents" in result["result"]:
        contents = result["result"]["contents"]
        if contents:
            markdown = contents[0].get("markdown", "")
            storage.write_file(
                project_name,
                f"output/extraction_results/{base_name}_markdown.md",
                markdown.encode('utf-8')
            )

    extraction_meta["quality_metrics"] = calculate_quality_metrics(result, markdown)
    return extraction_meta


def main(force_reextract: bool = False):
    """Main entry point."""
    storage = get_storage_service()

    documents = list_all_documents(storage)
    if not documents:
        return 1

    mode = "force" if force_reextract else "incremental"
    logger.info(f"Processing {len(documents)} documents (mode: {mode})")

    extraction_status = load_extraction_status(storage)
    all_results = []
    skipped_count = 0
    start_time = time.time()

    # Create temp directory for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        for i, doc in enumerate(documents, 1):
            filename = doc["name"]
            report_progress(i, len(documents), f"Processing: {filename}")
            set_document_context(i, len(documents), filename)

            # Skip already extracted (unless force mode)
            if not force_reextract and get_document_status(extraction_status, filename) == "completed":
                skipped_count += 1
                continue

            logger.info(f"[{i}/{len(documents)}] Processing: {filename}")

            result = process_document(storage, doc, temp_path)

            if result:
                extraction_meta = save_extraction(storage, filename, result)
                all_results.append(extraction_meta)

                update_document_status(
                    extraction_status, filename, "completed",
                    quality_score=extraction_meta['quality_metrics']['quality_score']
                )
            else:
                extraction_meta = {
                    "file_name": filename,
                    "processed_at": datetime.utcnow().isoformat(),
                    "quality_metrics": {"success": False},
                }
                all_results.append(extraction_meta)
                logger.error(f"Failed to extract: {filename}")

                update_document_status(extraction_status, filename, "failed")

            # Save status after each document (resume capability)
            save_extraction_status(storage, extraction_status)
            time.sleep(2)

    elapsed_time = time.time() - start_time

    # Save analysis
    analysis = {
        "generated_at": datetime.utcnow().isoformat(),
        "total_documents": len(documents),
        "skipped_documents": skipped_count,
        "processed_documents": len(documents) - skipped_count,
        "processing_time_seconds": elapsed_time,
        "documents": all_results,
    }
    storage.write_json(get_project_name(), "output/extraction_analysis.json", analysis)

    # Summary
    successful = [r for r in all_results if r.get("quality_metrics", {}).get("success")]
    processed = len(documents) - skipped_count
    failed = processed - len(successful)
    logger.info(f"Complete: {len(successful)}/{processed} succeeded, {skipped_count} skipped, {failed} failed ({elapsed_time/60:.1f}m)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
