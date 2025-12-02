"""
Test document processing with a single document using Agent Framework.

This script:
1. Routes documents intelligently to appropriate agent systems
2. Saves agent response to JSON
3. Saves extracted markdown to file
4. Shows summary of what was extracted

Routing:
- PDFs → Agent-based PDF extraction (2 agents)
- Excel files → openpyxl + agent enhancement
- Email files → extract-msg + agent enhancement

Usage:
    python scripts/test_single_document.py [document_path]

Example:
    python scripts/test_single_document.py "data/Spec/Protection and Control.pdf"
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Import agent-based extraction systems
from scripts.extraction.pdf_extraction_agents import process_pdf_with_agents_sync
from scripts.extraction.excel_extraction_agents import process_excel_with_agents_sync
from scripts.extraction.email_extraction_agents import process_email_with_agents_sync
from scripts.logging_config import get_logger

logger = get_logger(__name__)

# Load environment variables
load_dotenv()

# Configuration handled by agent modules

# Output directory
OUTPUT_DIR = Path("test_outputs")
OUTPUT_DIR.mkdir(exist_ok=True)


# Domain-specific extractors (like SLD) are available as optional plugins
# in scripts/extraction/plugins/


def save_results(file_path: Path, result: dict):
    """Save results to local files."""
    base_name = file_path.stem

    # Save raw JSON
    json_path = OUTPUT_DIR / f"{base_name}_raw.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # Extract and save markdown
    if "result" in result and "contents" in result["result"]:
        contents = result["result"]["contents"]
        if contents:
            markdown = contents[0].get("markdown", "")

            markdown_path = OUTPUT_DIR / f"{base_name}_markdown.md"
            with open(markdown_path, "w", encoding="utf-8") as f:
                f.write(markdown)

            return markdown

    return None


def analyze_results(file_path: Path, result: dict, markdown: str):
    """Analyze and log extraction results."""
    file_size = file_path.stat().st_size
    md_len = len(markdown) if markdown else 0
    words = len(markdown.split()) if markdown else 0

    # Check for figures
    fig_count = 0
    if "result" in result and "contents" in result["result"]:
        contents = result["result"]["contents"][0]
        if "figures" in contents:
            fig_count = len(contents.get("figures", []))

    logger.debug(f"Analysis: {file_path.suffix}, {file_size:,} bytes, {md_len:,} chars, {words:,} words, {fig_count} figures")


def list_available_documents():
    """
    List available documents to test.

    Excludes:
    - old/ - superseded documents
    - extracted_emails/ - duplicates from email attachments
    - TDS/ - subdirectory with duplicates
    - Subdirectories with communication equipment drawings (duplicates)
    """
    docs_dir = Path("data/Spec")

    if not docs_dir.exists():
        logger.error(f"Documents directory not found: {docs_dir}")
        return []

    # Directories to exclude (contain duplicates or superseded files)
    exclude_dirs = {
        "old",
        "extracted_emails",
        "TDS",
        "08052023 Commmunication equipment drawings"
    }

    files = []
    for file_path in docs_dir.rglob("*"):
        if file_path.is_file():
            # Skip if file is in any excluded directory
            if any(excl in file_path.parts for excl in exclude_dirs):
                continue

            # Only process supported formats
            if file_path.suffix.lower() in [".pdf", ".xlsx", ".xlsm", ".msg"]:
                files.append(file_path)

    return sorted(files)


def main():
    """Main entry point."""
    # Get document to test
    # Check if a valid file path was provided as argument
    file_path_arg = None
    if len(sys.argv) > 1:
        # Check if argument looks like a file path (not a command)
        potential_path = sys.argv[1]
        if not potential_path in ['process', '--test'] and (potential_path.endswith('.pdf') or potential_path.endswith('.xlsx') or potential_path.endswith('.xlsm') or potential_path.endswith('.msg')):
            file_path_arg = Path(potential_path)
            if not file_path_arg.exists():
                logger.error(f"File not found: {file_path_arg}")
                return

    if file_path_arg:
        file_path = file_path_arg
    else:
        # List available documents
        files = list_available_documents()

        if not files:
            logger.error("No documents found")
            return

        # Interactive selection
        for i, f in enumerate(files, 1):
            print(f"  {i}. {f.name} ({f.suffix}) - {f.stat().st_size:,} bytes")

        # Ask user to pick
        try:
            choice = input(f"\nSelect document (1-{len(files)}), or press Enter for first PDF: ").strip()
            if not choice:
                # Find first PDF
                pdf_files = [f for f in files if f.suffix.lower() == ".pdf"]
                if pdf_files:
                    file_path = pdf_files[0]
                else:
                    file_path = files[0]
            else:
                idx = int(choice) - 1
                if 0 <= idx < len(files):
                    file_path = files[idx]
                else:
                    logger.error("Invalid choice")
                    return
        except (ValueError, KeyboardInterrupt):
            return

    logger.info(f"Processing {file_path.name}")

    result = None
    processing_method = "unknown"

    if file_path.suffix.lower() == ".pdf":
        processing_method = "agent_based_pdf_extraction"
        result = process_pdf_with_agents_sync(file_path)

    elif file_path.suffix.lower() in ['.xlsx', '.xlsm']:
        processing_method = "excel_with_agent_enhancement"
        result = process_excel_with_agents_sync(file_path)

    elif file_path.suffix.lower() == ".msg":
        processing_method = "email_with_agent_enhancement"
        result = process_email_with_agents_sync(file_path)

    else:
        logger.error(f"Unsupported file type: {file_path.suffix}")
        return

    if not result:
        logger.error("Failed to process document")
        return

    # Save results
    markdown = save_results(file_path, result)

    # Analyze
    analyze_results(file_path, result, markdown)

    md_len = len(markdown) if markdown else 0
    logger.info(f"Complete: {processing_method}, {md_len:,} chars output to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
