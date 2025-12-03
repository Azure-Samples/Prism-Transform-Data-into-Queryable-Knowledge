"""
Process all documents using Agent Framework with intelligent routing.

This script uses a hybrid agent-based architecture:
- PDFs → Agent-based extraction with vision (for images) or text extraction
- Excel files → openpyxl extraction + agent enhancement
- Email files → extract-msg + agent enhancement

All documents get validation and semantic enhancement through specialized agents.

Usage:
    python main.py process --project myproject

Outputs:
    - projects/{project}/output/extraction_results/ - All extracted content
    - projects/{project}/output/extraction_analysis.json - Detailed quality metrics
    - projects/{project}/output/extraction_report.md - Human-readable report
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, List

# Import extraction systems
# Use hybrid extraction (PyMuPDF4LLM + Vision validation) for PDFs
from scripts.extraction.pdf_extraction_hybrid import process_pdf_hybrid_sync
from scripts.extraction.excel_extraction_agents import process_excel_with_agents_sync
from scripts.extraction.email_extraction_agents import process_email_with_agents_sync
from scripts.logging_config import get_logger

# Logger
logger = get_logger(__name__)

# Import progress reporting (optional - only works when called from pipeline service)
try:
    from apps.api.app.services.progress_tracker import report_progress, set_document_context
except ImportError:
    # Fallback if not running through API
    def report_progress(current: int, total: int, message: str = "") -> None:
        pass
    def set_document_context(doc_num: int, total_docs: int, doc_name: str = "") -> None:
        pass

# Load environment variables
load_dotenv()

# Configuration
# Note: Azure OpenAI configuration is now handled by agent modules

# Project name - set via environment variable or parameter
PROJECT_NAME = os.getenv("PRISM_PROJECT_NAME", "_example")

# Project directory paths
PROJECT_DIR = Path("projects") / PROJECT_NAME
DOCS_DIR = PROJECT_DIR / "documents"
OUTPUT_DIR = PROJECT_DIR / "output" / "extraction_results"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def list_all_documents() -> List[Path]:
    """
    Get all documents to process.

    Excludes:
    - old/ - superseded documents
    - extracted_emails/ - duplicates from email attachments
    - TDS/ - subdirectory with duplicates
    - Subdirectories with communication equipment drawings (duplicates)

    Returns:
        List of Path objects for documents to process
    """
    if not DOCS_DIR.exists():
        logger.error(f"Documents directory not found: {DOCS_DIR}")
        return []

    # Directories to exclude (contain duplicates or superseded files)
    exclude_dirs = {
        "old",
        "extracted_emails",
        "TDS",
        "08052023 Commmunication equipment drawings"
    }

    files = []
    for file_path in DOCS_DIR.rglob("*"):
        if file_path.is_file():
            # Skip if file is in any excluded directory
            if any(excl in file_path.parts for excl in exclude_dirs):
                continue

            # Only process supported formats
            if file_path.suffix.lower() in [".pdf", ".xlsx", ".xlsm", ".msg"]:
                files.append(file_path)

    return sorted(files)


# All PDFs go through generic agent-based extraction
# Domain-specific extractors (like SLD) are available as optional plugins
# in scripts/extraction/plugins/


# Email and Content Understanding processing moved to specialized agent modules


def save_extraction(file_path: Path, result: dict) -> Dict:
    """Save extraction results and return metadata."""
    base_name = file_path.stem
    relative_path = file_path.relative_to(DOCS_DIR)

    # Create subdirectory structure
    output_subdir = OUTPUT_DIR / relative_path.parent
    output_subdir.mkdir(parents=True, exist_ok=True)

    extraction_meta = {
        "file_name": file_path.name,
        "file_path": str(relative_path),
        "file_type": file_path.suffix,
        "file_size": file_path.stat().st_size,
        "processed_at": datetime.utcnow().isoformat(),
    }

    # Save raw JSON
    json_path = output_subdir / f"{base_name}_raw.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    extraction_meta["raw_json_path"] = str(json_path.relative_to(OUTPUT_DIR))

    # Extract and save markdown
    markdown = ""
    if "result" in result and "contents" in result["result"]:
        contents = result["result"]["contents"]
        if contents:
            markdown = contents[0].get("markdown", "")

            markdown_path = output_subdir / f"{base_name}_markdown.md"
            with open(markdown_path, "w", encoding="utf-8") as f:
                f.write(markdown)
            extraction_meta["markdown_path"] = str(markdown_path.relative_to(OUTPUT_DIR))

    # Calculate quality metrics
    extraction_meta["quality_metrics"] = calculate_quality_metrics(
        file_path, result, markdown
    )

    return extraction_meta


def calculate_quality_metrics(file_path: Path, result: dict, markdown: str) -> Dict:
    """Calculate quality metrics for extraction."""
    metrics = {
        "success": True,
        "markdown_length": len(markdown),
        "markdown_lines": len(markdown.split("\n")),
        "word_count": len(markdown.split()),
        "has_tables": "|" in markdown and markdown.count("|") > 10,
        "table_count": markdown.count("\n|") if "|" in markdown else 0,
    }

    # Check for content in result
    if "result" in result and "contents" in result["result"]:
        contents = result["result"]["contents"]
        if contents:
            content = contents[0]

            # Figures/images
            figures = content.get("figures", [])
            metrics["figure_count"] = len(figures)
            metrics["has_figures"] = len(figures) > 0

            # Tables
            tables = content.get("tables", [])
            metrics["tables_detected"] = len(tables)

            # Sections
            sections = content.get("sections", [])
            metrics["section_count"] = len(sections)

            # Pages
            pages = content.get("pages", [])
            metrics["page_count"] = len(pages)

    # File type specific checks
    if file_path.suffix.lower() == ".pdf":
        # PDFs should have substantial content
        metrics["pdf_quality"] = "good" if metrics["word_count"] > 100 else "poor"
    elif file_path.suffix.lower() in [".xlsx", ".xlsm"]:
        # Excel should have tables
        metrics["excel_quality"] = "good" if metrics["has_tables"] else "poor"
    elif file_path.suffix.lower() == ".msg":
        # Email should have content
        metrics["email_quality"] = "good" if metrics["word_count"] > 50 else "poor"

    # Overall quality score (0-100)
    score = 0
    if metrics["word_count"] > 0:
        score += 30
    if metrics["word_count"] > 500:
        score += 20
    if metrics.get("has_figures"):
        score += 15
    if metrics.get("has_tables"):
        score += 15
    if metrics.get("page_count", 0) > 0:
        score += 10
    if metrics.get("section_count", 0) > 0:
        score += 10

    metrics["quality_score"] = min(score, 100)

    return metrics


def generate_analysis_report(all_results: List[Dict]) -> str:
    """Generate human-readable analysis report."""
    report_lines = [
        "# Document Extraction Quality Report",
        "",
        f"**Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"**Total Documents**: {len(all_results)}",
        "",
        "---",
        "",
    ]

    # Summary statistics
    successful = [r for r in all_results if r.get("quality_metrics", {}).get("success")]
    failed = [r for r in all_results if not r.get("quality_metrics", {}).get("success")]

    report_lines.extend([
        "## Summary",
        "",
        f"- **Successful**: {len(successful)} documents",
        f"- **Failed**: {len(failed)} documents",
        f"- **Success Rate**: {len(successful)/max(len(all_results), 1)*100:.1f}%",
        "",
    ])

    # Aggregate metrics
    total_words = sum(r.get("quality_metrics", {}).get("word_count", 0) for r in successful)
    total_tables = sum(r.get("quality_metrics", {}).get("tables_detected", 0) for r in successful)
    total_figures = sum(r.get("quality_metrics", {}).get("figure_count", 0) for r in successful)
    total_pages = sum(r.get("quality_metrics", {}).get("page_count", 0) for r in successful)

    avg_quality = sum(r.get("quality_metrics", {}).get("quality_score", 0) for r in successful) / max(len(successful), 1)

    report_lines.extend([
        "## Aggregate Metrics",
        "",
        f"- **Total Words Extracted**: {total_words:,}",
        f"- **Total Tables Detected**: {total_tables}",
        f"- **Total Figures/Images**: {total_figures}",
        f"- **Total Pages Processed**: {total_pages}",
        f"- **Average Quality Score**: {avg_quality:.1f}/100",
        "",
    ])

    # Document-by-document breakdown
    report_lines.extend([
        "---",
        "",
        "## Document-by-Document Analysis",
        "",
    ])

    for i, result in enumerate(all_results, 1):
        metrics = result.get("quality_metrics", {})
        file_name = result.get("file_name", "Unknown")
        file_type = result.get("file_type", "")
        file_size_mb = result.get("file_size", 0) / 1024 / 1024

        report_lines.extend([
            f"### {i}. {file_name}",
            "",
            f"**File Type**: {file_type}  ",
            f"**File Size**: {file_size_mb:.2f} MB  ",
            f"**Quality Score**: {metrics.get('quality_score', 0)}/100",
            "",
        ])

        if metrics.get("success"):
            report_lines.extend([
                "**Extraction Results**:",
                f"- Words: {metrics.get('word_count', 0):,}",
                f"- Lines: {metrics.get('markdown_lines', 0):,}",
                f"- Pages: {metrics.get('page_count', 0)}",
                f"- Tables: {metrics.get('tables_detected', 0)}",
                f"- Figures/Images: {metrics.get('figure_count', 0)}",
                f"- Sections: {metrics.get('section_count', 0)}",
                "",
            ])

            # Type-specific quality
            if "pdf_quality" in metrics:
                report_lines.append(f"**PDF Quality**: {metrics['pdf_quality']}")
            elif "excel_quality" in metrics:
                report_lines.append(f"**Excel Quality**: {metrics['excel_quality']}")
            elif "email_quality" in metrics:
                report_lines.append(f"**Email Quality**: {metrics['email_quality']}")

            report_lines.append("")

            # Files location
            report_lines.extend([
                "**Outputs**:",
                f"- Markdown: `{result.get('markdown_path', 'N/A')}`",
                f"- Raw JSON: `{result.get('raw_json_path', 'N/A')}`",
                "",
            ])
        else:
            report_lines.extend([
                "**Status**: FAILED",
                "",
            ])

    # Recommendations
    report_lines.extend([
        "---",
        "",
        "## Recommendations",
        "",
    ])

    # Find low quality documents
    low_quality = [r for r in successful if r.get("quality_metrics", {}).get("quality_score", 100) < 50]

    if low_quality:
        report_lines.extend([
            "### Low Quality Extractions",
            "",
            "The following documents had low quality scores and may need review:",
            "",
        ])
        for r in low_quality:
            score = r.get("quality_metrics", {}).get("quality_score", 0)
            report_lines.append(f"- **{r.get('file_name')}** (Score: {score}/100)")
        report_lines.append("")

    if failed:
        report_lines.extend([
            "### Failed Extractions",
            "",
            "The following documents failed to process:",
            "",
        ])
        for r in failed:
            report_lines.append(f"- **{r.get('file_name')}**")
        report_lines.append("")

    # Success cases
    high_quality = [r for r in successful if r.get("quality_metrics", {}).get("quality_score", 0) >= 80]
    if high_quality:
        report_lines.extend([
            "### High Quality Extractions",
            "",
            f"{len(high_quality)} documents had excellent extraction quality (score >= 80):",
            "",
        ])
        for r in high_quality:
            score = r.get("quality_metrics", {}).get("quality_score", 0)
            report_lines.append(f"- **{r.get('file_name')}** (Score: {score}/100)")
        report_lines.append("")

    report_lines.extend([
        "---",
        "",
        "## Next Steps",
        "",
        "1. Review low-quality extractions manually",
        "2. Check failed documents for issues",
        "3. Verify tables and figures were extracted correctly",
        "4. If satisfied, proceed to index creation and upload",
        "",
    ])

    return "\n".join(report_lines)


def load_extraction_status() -> Dict:
    """Load extraction status from JSON file."""
    status_path = PROJECT_DIR / "output" / "extraction_status.json"
    if status_path.exists():
        try:
            with open(status_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load extraction status: {e}")
    return {"documents": {}}


def save_extraction_status(status: Dict) -> None:
    """Save extraction status to JSON file."""
    status_path = PROJECT_DIR / "output" / "extraction_status.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    with open(status_path, 'w') as f:
        json.dump(status, f, indent=2)


def get_output_path(file_path: Path) -> Path:
    """Get the expected output markdown path for a document."""
    safe_name = file_path.stem.replace(" ", "_")
    return OUTPUT_DIR / f"{safe_name}_markdown.md"


def get_document_status(status: Dict, file_path: Path) -> str:
    """
    Get extraction status for a document (completed/failed/pending).

    Also verifies the output file actually exists - if status says completed
    but output file is missing, returns 'pending' to trigger re-extraction.
    """
    rel_path = str(file_path.relative_to(DOCS_DIR))
    doc_info = status.get("documents", {}).get(rel_path, {})
    stored_status = doc_info.get("status", "pending")

    # If status says completed, verify output file actually exists
    if stored_status == "completed":
        output_path = get_output_path(file_path)
        if not output_path.exists():
            logger.warning(f"Status says completed but output missing: {file_path.name}")
            return "pending"

    return stored_status


def update_document_status(status: Dict, file_path: Path, doc_status: str, **kwargs) -> None:
    """Update extraction status for a document."""
    rel_path = str(file_path.relative_to(DOCS_DIR))
    if "documents" not in status:
        status["documents"] = {}
    status["documents"][rel_path] = {
        "status": doc_status,
        "updated_at": datetime.utcnow().isoformat(),
        **kwargs
    }


def main(force_reextract: bool = False):
    """Main entry point.

    Args:
        force_reextract: If True, re-process all documents even if already extracted
    """
    files = list_all_documents()
    if not files:
        logger.error("No documents found")
        return 1

    mode = "force" if force_reextract else "incremental"
    logger.info(f"Processing {len(files)} documents (mode: {mode})")

    # Load extraction status for incremental processing
    extraction_status = load_extraction_status()
    skipped_count = 0

    all_results = []
    start_time = time.time()

    for i, file_path in enumerate(files, 1):
        # Report progress to API (for UI progress bar)
        report_progress(i, len(files), f"Processing: {file_path.name}")
        set_document_context(i, len(files), file_path.name)

        # Skip already extracted (unless force mode)
        doc_status = get_document_status(extraction_status, file_path)
        if not force_reextract and doc_status == "completed":
            skipped_count += 1
            continue

        # Route by file type
        processing_method = "unknown"
        result = None
        ext = file_path.suffix.lower()

        if ext == ".pdf":
            processing_method = "hybrid_pymupdf4llm_vision"
            result = process_pdf_hybrid_sync(file_path, project_path=PROJECT_DIR)
        elif ext in ['.xlsx', '.xlsm']:
            processing_method = "excel_with_agent_enhancement"
            result = process_excel_with_agents_sync(file_path)
        elif ext == ".msg":
            processing_method = "email_with_agent_enhancement"
            result = process_email_with_agents_sync(file_path)
        else:
            logger.error(f"Unsupported file type: {ext} ({file_path.name})")

        if result:
            extraction_meta = save_extraction(file_path, result)
            extraction_meta["processing_method"] = processing_method
            all_results.append(extraction_meta)

            # Update extraction status
            update_document_status(
                extraction_status, file_path, "completed",
                quality_score=extraction_meta['quality_metrics']['quality_score'],
                output_file=extraction_meta.get('markdown_path', ''),
                processing_method=processing_method
            )
        else:
            # Record failed attempt
            extraction_meta = {
                "file_name": file_path.name,
                "file_path": str(file_path.relative_to(DOCS_DIR)),
                "file_type": file_path.suffix,
                "file_size": file_path.stat().st_size,
                "processed_at": datetime.utcnow().isoformat(),
                "processing_method": processing_method,
                "quality_metrics": {"success": False},
            }
            all_results.append(extraction_meta)
            logger.error(f"Failed to extract: {file_path.name}")

            update_document_status(
                extraction_status, file_path, "failed",
                error="Extraction returned no result",
                processing_method=processing_method
            )

        # Save status after each document (for resume capability)
        save_extraction_status(extraction_status)
        time.sleep(2)

    elapsed_time = time.time() - start_time

    # Save results
    analysis_json_path = Path("projects") / PROJECT_NAME / "output" / "extraction_analysis.json"
    with open(analysis_json_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.utcnow().isoformat(),
            "total_documents": len(files),
            "skipped_documents": skipped_count,
            "processed_documents": len(files) - skipped_count,
            "processing_time_seconds": elapsed_time,
            "documents": all_results,
        }, f, indent=2, ensure_ascii=False)

    report = generate_analysis_report(all_results)
    report_path = Path("projects") / PROJECT_NAME / "output" / "extraction_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    # Summary
    successful = [r for r in all_results if r.get("quality_metrics", {}).get("success")]
    processed = len(files) - skipped_count
    failed = processed - len(successful)
    logger.info(f"Complete: {len(successful)}/{processed} succeeded, {skipped_count} skipped, {failed} failed ({elapsed_time/60:.1f}m)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
