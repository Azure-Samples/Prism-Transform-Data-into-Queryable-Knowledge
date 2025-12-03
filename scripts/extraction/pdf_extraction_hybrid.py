"""
Hybrid PDF Extraction: PyMuPDF4LLM (local) + Vision (validation).

This module implements a two-pass extraction approach:
1. PyMuPDF4LLM for fast, local markdown extraction (free)
2. GPT-4.1 Vision for validation/enhancement of pages with images

Key insight: Vision VALIDATES the extraction rather than extracting from scratch.
This is more accurate because Vision compares the markdown against the page image.
"""

import os
import json
import base64
import asyncio
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass
import fitz  # PyMuPDF

# Import pymupdf.layout BEFORE pymupdf4llm to activate advanced layout analysis
# This enables automatic header/footer detection and better semantic understanding
try:
    import pymupdf.layout
    LAYOUT_AVAILABLE = True
except ImportError:
    LAYOUT_AVAILABLE = False

import pymupdf4llm
from dotenv import load_dotenv

from agent_framework import ChatMessage, DataContent, Role, TextContent
from agent_framework.azure import AzureOpenAIChatClient
from scripts.logging_config import get_logger

# Import progress reporting
try:
    from apps.api.app.services.progress_tracker import report_page_progress
except ImportError:
    # Fallback if not running through API
    def report_page_progress(page_num: int, total_pages: int, message: str = "") -> None:
        pass

# Load environment
load_dotenv()

# Logger
logger = get_logger(__name__)

# Configuration
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
AZURE_OPENAI_CHAT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME", "gpt-5-chat")

# Cache for agents
_agent_cache: Dict[str, any] = {}


# Vision Validator Instructions
VISION_VALIDATOR_INSTRUCTIONS = """You are a document extraction VALIDATOR and ENHANCER.

You receive:
1. A page image from a PDF document
2. An existing markdown extraction of that page

Your job is to VALIDATE and ENHANCE the extraction, NOT extract from scratch.

## VALIDATION CHECKLIST:
Check that the markdown extraction captures:
- [ ] All text paragraphs (verify against image)
- [ ] All table rows and columns (count them!)
- [ ] All list items and bullet points
- [ ] All headers and section titles
- [ ] Page numbers, headers, footers if present

## ENHANCEMENT TASKS:
1. **Describe images/diagrams**: For any visual elements, add detailed descriptions
2. **Fix missing content**: Add any text that was missed
3. **Correct errors**: Fix any structural or content errors
4. **Preserve structure**: Keep the markdown hierarchy intact

## OUTPUT FORMAT:
Return the validated/enhanced markdown directly. Include:
- Original correct content (preserved)
- Missing content (added with comment: <!-- ADDED -->)
- Image descriptions (as: **[Image: description]** or ![description](image))
- Error corrections (with comment: <!-- CORRECTED -->)

If the extraction is perfect and complete, return it as-is with only image descriptions added.

Be thorough - accuracy is critical."""


@dataclass
class PageAnalysis:
    """Analysis result for a PDF page."""
    has_images: bool
    has_complex_drawings: bool
    image_count: int
    drawing_count: int
    text_length: int
    needs_vision: bool
    reason: str


# Cache for repeated image detection
_repeated_images_cache: Dict[str, set] = {}


def get_repeated_image_xrefs(pdf_path: Path) -> set:
    """
    Find images that appear on many pages (likely headers/footers/logos).

    These should be excluded from Vision validation since they:
    - Don't contain document content
    - Are the same on every page
    - Would waste Vision calls

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Set of xref IDs for repeated images
    """
    cache_key = str(pdf_path)
    if cache_key in _repeated_images_cache:
        return _repeated_images_cache[cache_key]

    from collections import Counter

    doc = fitz.open(pdf_path)
    all_xrefs = []

    for page in doc:
        for img in page.get_images():
            all_xrefs.append(img[0])

    doc.close()

    # Images appearing on >10 pages are likely headers/footers
    xref_counts = Counter(all_xrefs)
    repeated = {xref for xref, count in xref_counts.items() if count > 10}

    _repeated_images_cache[cache_key] = repeated
    return repeated


def get_client():
    """Lazy initialization of Azure OpenAI client."""
    global _agent_cache
    if '_client' not in _agent_cache:
        logger.debug("Initializing Azure OpenAI client")
        _agent_cache['_client'] = AzureOpenAIChatClient(
            api_key=AZURE_OPENAI_API_KEY,
            endpoint=AZURE_OPENAI_ENDPOINT,
            deployment_name=AZURE_OPENAI_CHAT_DEPLOYMENT,
            api_version=AZURE_OPENAI_API_VERSION
        )
    return _agent_cache['_client']


def get_validator_agent(project_instructions: Optional[str] = None):
    """Get or create a Vision validator agent."""
    cache_key = f"validator_{hash(project_instructions or 'default')}"

    if cache_key not in _agent_cache:
        client = get_client()

        # Combine project instructions with validation instructions
        if project_instructions:
            instructions = f"""{project_instructions}

---

{VISION_VALIDATOR_INSTRUCTIONS}"""
        else:
            instructions = VISION_VALIDATOR_INSTRUCTIONS

        logger.debug(f"Creating Vision_Validator agent")
        _agent_cache[cache_key] = client.create_agent(
            name="Vision_Validator",
            instructions=instructions
        )

    return _agent_cache[cache_key]


def analyze_page(page: fitz.Page, local_markdown: str, repeated_xrefs: set = None) -> PageAnalysis:
    """
    Analyze a PDF page to determine if Vision validation is needed.

    Smart filtering:
    - Excludes repeated images (headers/footers/logos that appear on many pages)
    - Higher threshold for "complex drawings" (50+ vs old 5+)

    Args:
        page: PyMuPDF page object
        local_markdown: Markdown extracted by PyMuPDF4LLM
        repeated_xrefs: Set of image xrefs to exclude (repeated across pages)

    Returns:
        PageAnalysis with determination of whether Vision is needed
    """
    images = page.get_images()
    drawings = page.get_drawings()

    # Filter out repeated images (headers/footers/logos)
    if repeated_xrefs:
        real_images = [img for img in images if img[0] not in repeated_xrefs]
    else:
        real_images = images

    has_images = len(real_images) > 0
    # Raised threshold: 50+ drawings suggests complex diagrams/tables
    # (was 5, which triggered on almost every page)
    has_complex_drawings = len(drawings) > 50

    # Determine if Vision validation is needed
    needs_vision = has_images or has_complex_drawings

    if has_images:
        reason = f"Page has {len(real_images)} content image(s)"
    elif has_complex_drawings:
        reason = f"Page has {len(drawings)} vector elements (complex layout)"
    else:
        reason = "Text-only page"

    return PageAnalysis(
        has_images=has_images,
        has_complex_drawings=has_complex_drawings,
        image_count=len(real_images),
        drawing_count=len(drawings),
        text_length=len(local_markdown),
        needs_vision=needs_vision,
        reason=reason
    )


def render_page_to_b64(page: fitz.Page, scale: float = 2.0) -> str:
    """
    Render a PDF page to base64-encoded PNG.

    Args:
        page: PyMuPDF page object
        scale: Resolution multiplier (2.0 = 2x resolution)

    Returns:
        Base64-encoded PNG string
    """
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat)
    img_bytes = pix.tobytes("png")
    return base64.b64encode(img_bytes).decode('utf-8')


def extract_page_local(pdf_path: Path, page_num: int) -> str:
    """
    Extract a single page using PyMuPDF4LLM.

    When pymupdf-layout is available, automatically filters headers/footers.

    Args:
        pdf_path: Path to the PDF file
        page_num: Page number (0-indexed)

    Returns:
        Markdown string for the page
    """
    try:
        # Build extraction kwargs
        kwargs = {
            "pages": [page_num],
            "write_images": False,  # We handle images via Vision
            "page_chunks": True  # Get per-page results
        }

        # When pymupdf-layout is available, filter headers/footers automatically
        if LAYOUT_AVAILABLE:
            kwargs["header"] = False
            kwargs["footer"] = False

        result = pymupdf4llm.to_markdown(str(pdf_path), **kwargs)

        # Handle different return types:
        # - With pymupdf-layout: returns string directly
        # - Without (legacy mode): returns list of dicts with 'text' key
        if isinstance(result, str):
            return result
        if result and len(result) > 0:
            if isinstance(result[0], dict):
                return result[0].get('text', '')
            return str(result[0])
        return ""
    except Exception as e:
        logger.warning(f"PyMuPDF4LLM extraction failed: {e}")
        # Fallback to basic text extraction
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        text = page.get_text()
        doc.close()
        return text


async def validate_with_vision(
    page_image_b64: str,
    local_markdown: str,
    project_instructions: Optional[str] = None
) -> Dict:
    """
    Validate local extraction using Vision.

    Args:
        page_image_b64: Base64-encoded page image
        local_markdown: Markdown from PyMuPDF4LLM
        project_instructions: Optional project-specific instructions

    Returns:
        Dict with validated markdown and any corrections
    """
    validator_agent = get_validator_agent(project_instructions)

    # Construct the validation message
    validation_message = ChatMessage(
        role=Role.USER,
        contents=[
            TextContent(text=f"""Validate this extraction against the page image.

LOCAL EXTRACTION:
```markdown
{local_markdown}
```

Check for completeness and accuracy. Add descriptions for any images/diagrams.
Return the validated/enhanced markdown."""),
            DataContent(
                uri=f"data:image/png;base64,{page_image_b64}",
                media_type="image/png"
            )
        ]
    )

    try:
        result = await validator_agent.run(validation_message)
        validated_markdown = result.text

        # Check if corrections were made
        corrections_made = (
            "<!-- ADDED -->" in validated_markdown or
            "<!-- CORRECTED -->" in validated_markdown or
            "[Image:" in validated_markdown
        )

        return {
            "markdown": validated_markdown,
            "corrections_made": corrections_made,
            "status": "validated"
        }
    except Exception as e:
        logger.error(f"Vision validation failed: {e}")
        # Return original on failure
        return {
            "markdown": local_markdown,
            "corrections_made": False,
            "status": "fallback",
            "error": str(e)
        }


async def process_page_hybrid(
    pdf_path: Path,
    page_num: int,
    page_count: int,
    project_instructions: Optional[str] = None,
    repeated_xrefs: set = None
) -> Dict:
    """
    Process a single PDF page with hybrid approach.

    Args:
        pdf_path: Path to the PDF
        page_num: Page number (0-indexed)
        page_count: Total pages in document
        project_instructions: Optional project-specific instructions
        repeated_xrefs: Set of image xrefs to exclude (headers/footers)

    Returns:
        Dict with markdown and processing metadata
    """
    logger.debug(f"Processing page {page_num + 1}/{page_count}")

    # Step 1: Local extraction with PyMuPDF4LLM
    local_md = extract_page_local(pdf_path, page_num)

    # Step 2: Analyze page (with smart image filtering)
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    analysis = analyze_page(page, local_md, repeated_xrefs)

    if analysis.needs_vision:
        # Step 3: Vision validation for pages with images
        logger.debug(f"Page {page_num + 1}: Vision validation - {analysis.reason}")
        page_image_b64 = render_page_to_b64(page)
        doc.close()

        result = await validate_with_vision(
            page_image_b64, local_md, project_instructions
        )
        status = "OK" if result["status"] == "validated" else f"FALLBACK ({result.get('error', 'unknown')})"
        logger.debug(f"Page {page_num + 1}: Vision {status}")

        return {
            "markdown": result["markdown"],
            "processing_mode": "validated" if result["status"] == "validated" else "fallback",
            "corrections_made": result.get("corrections_made", False),
            "analysis": {
                "images": analysis.image_count,
                "drawings": analysis.drawing_count
            }
        }
    else:
        # Trust local extraction for text-only pages
        logger.debug(f"Page {page_num + 1}: Local extraction ({len(local_md)} chars)")
        doc.close()

        return {
            "markdown": local_md,
            "processing_mode": "local",
            "corrections_made": False,
            "analysis": {
                "images": 0,
                "drawings": analysis.drawing_count
            }
        }


async def process_pdf_hybrid(
    pdf_path: Path,
    project_path: Optional[Path] = None,
    project_instructions: Optional[str] = None
) -> Dict:
    """
    Process entire PDF with hybrid extraction.

    Args:
        pdf_path: Path to the PDF file
        project_path: Optional path to project directory (to load config)
        project_instructions: Optional explicit instructions

    Returns:
        Dict compatible with existing pipeline format
    """
    # Load project instructions if not provided
    if project_instructions is None and project_path is not None:
        config_path = project_path / "config.json"
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                project_instructions = config.get('extraction_instructions')
            except Exception as e:
                logger.warning(f"Could not load project config: {e}")

    try:
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        doc.close()

        # Get repeated images once (for smart filtering)
        repeated_xrefs = get_repeated_image_xrefs(pdf_path)

        layout_status = "layout+" if LAYOUT_AVAILABLE else "basic"
        logger.info(f"Extracting {pdf_path.name} ({page_count} pages, {layout_status}, {len(repeated_xrefs)} repeated imgs filtered)")

        # Process all pages
        all_page_results = []
        local_pages = 0
        validated_pages = 0
        fallback_pages = 0

        for page_num in range(page_count):
            # Report page progress (1-indexed for display)
            report_page_progress(page_num + 1, page_count, "Extracting")

            page_result = await process_page_hybrid(
                pdf_path, page_num, page_count, project_instructions, repeated_xrefs
            )
            all_page_results.append(f"## Page {page_num + 1}\n\n{page_result['markdown']}")

            # Track processing mode
            mode = page_result.get('processing_mode', 'unknown')
            if mode == 'local':
                local_pages += 1
            elif mode == 'validated':
                validated_pages += 1
            else:
                fallback_pages += 1

        # Combine results
        final_markdown = "\n\n---\n\n".join(all_page_results)

        # Create result structure
        result = {
            "status": "Succeeded",
            "method": "hybrid_pymupdf4llm_vision",
            "result": {
                "contents": [{
                    "markdown": final_markdown
                }],
                "pages": [{"pageNumber": i+1} for i in range(page_count)],
                "processing_summary": {
                    "local_pages": local_pages,
                    "validated_pages": validated_pages,
                    "fallback_pages": fallback_pages,
                    "total_vision_calls": validated_pages
                }
            }
        }

        logger.info(
            f"Extraction complete: {len(final_markdown):,} chars | "
            f"Local: {local_pages} | Vision: {validated_pages} | Fallback: {fallback_pages}"
        )

        return result

    except Exception as e:
        logger.error(f"Hybrid extraction failed: {e}", exc_info=True)
        return None


def process_pdf_hybrid_sync(
    pdf_path: Path,
    project_path: Optional[Path] = None,
    project_instructions: Optional[str] = None
) -> Dict:
    """Synchronous wrapper for async hybrid processing."""
    return asyncio.run(process_pdf_hybrid(pdf_path, project_path, project_instructions))
