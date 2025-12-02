"""
Email extraction utility for .msg files (Outlook emails).

This module provides helper functions used by email_extraction_agents.py:
- format_email_as_markdown(): Convert .msg file to markdown format

Note: This is a utility module, not meant to be run standalone.
"""

import os
from pathlib import Path
from datetime import datetime
import extract_msg
from scripts.logging_config import get_logger

logger = get_logger(__name__)

# Configuration
SOURCE_DIR = Path("data/Spec")
OUTPUT_DIR = Path("data/Spec/extracted_emails")
ATTACHMENTS_DIR = OUTPUT_DIR / "attachments"


def format_email_as_markdown(msg_path: Path) -> str:
    """
    Extract and format .msg file as markdown.

    Args:
        msg_path: Path to .msg file

    Returns:
        Formatted markdown string
    """
    try:
        # Open the message
        msg = extract_msg.Message(str(msg_path))

        # Build markdown content
        markdown = []

        # Header
        markdown.append(f"# Email: {msg.subject or 'No Subject'}")
        markdown.append("")

        # Metadata
        markdown.append("## Email Metadata")
        markdown.append("")
        markdown.append(f"**From:** {msg.sender or 'Unknown'}")
        markdown.append(f"**To:** {msg.to or 'Unknown'}")
        if msg.cc:
            markdown.append(f"**CC:** {msg.cc}")
        if msg.date:
            markdown.append(f"**Date:** {msg.date}")
        markdown.append("")

        # Attachments section
        if msg.attachments:
            markdown.append("## Attachments")
            markdown.append("")
            for i, attachment in enumerate(msg.attachments, 1):
                att_name = getattr(attachment, 'longFilename', None) or getattr(attachment, 'shortFilename', f'attachment_{i}')
                att_size = getattr(attachment, 'size', 0)
                markdown.append(f"{i}. **{att_name}** ({att_size:,} bytes)")

                # Save attachment if it's a document
                if att_name and any(att_name.lower().endswith(ext) for ext in ['.pdf', '.xlsx', '.docx', '.txt']):
                    try:
                        att_folder = ATTACHMENTS_DIR / msg_path.stem
                        att_folder.mkdir(parents=True, exist_ok=True)
                        att_path = att_folder / att_name
                        attachment.save(customPath=str(att_folder))
                        markdown.append(f"   - Extracted to: `{att_path.relative_to(SOURCE_DIR)}`")
                    except Exception as e:
                        logger.warning(f"Failed to save attachment {att_name}: {e}")
                        markdown.append(f"   - Could not extract: {e}")

            markdown.append("")

        # Email body
        markdown.append("## Email Body")
        markdown.append("")

        # Try to get plain text body first, fall back to HTML
        body = msg.body

        if not body and msg.htmlBody:
            # Simple HTML to text conversion
            import re
            html = msg.htmlBody
            # Remove scripts and styles
            html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
            html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
            # Remove HTML tags
            html = re.sub(r'<[^>]+>', ' ', html)
            # Decode HTML entities
            import html as html_module
            html = html_module.unescape(html)
            # Clean up whitespace
            html = re.sub(r'\s+', ' ', html)
            body = html.strip()

        if body:
            # Clean up the body
            body = body.strip()
            # Add to markdown
            markdown.append(body)
        else:
            markdown.append("*[No body content]*")

        markdown.append("")

        # Close the message
        msg.close()

        result = "\n".join(markdown)

        size_kb = len(result.encode('utf-8')) / 1024
        if size_kb > 900:
            logger.warning(f"Email {msg_path.name} close to 1MB limit ({size_kb:.1f} KB)")

        return result

    except Exception as e:
        logger.error(f"Failed to extract {msg_path.name}: {e}")
        return None


# Note: Standalone execution removed. This module is now a utility for email_extraction_agents.py
