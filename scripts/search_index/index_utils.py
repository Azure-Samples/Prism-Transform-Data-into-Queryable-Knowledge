"""
Shared utilities for Azure AI Search index operations.

Azure AI Search index naming requirements:
- Must contain only lowercase letters, digits, or dashes
- Cannot start or end with dashes
- Limited to 128 characters
"""

import os
import re
from scripts.logging_config import get_logger

logger = get_logger(__name__)


def sanitize_index_name(name: str) -> str:
    """
    Sanitize a string to be a valid Azure AI Search index name.

    Rules applied:
    - Convert to lowercase
    - Replace spaces and underscores with dashes
    - Remove any characters that aren't lowercase letters, digits, or dashes
    - Remove leading/trailing dashes
    - Collapse multiple consecutive dashes into one
    - Truncate to 128 characters

    Args:
        name: The raw name to sanitize

    Returns:
        A valid Azure AI Search index name
    """
    if not name:
        return "default"

    # Convert to lowercase
    sanitized = name.lower()

    # Replace common separators with dashes
    sanitized = sanitized.replace(" ", "-").replace("_", "-")

    # Remove any character that isn't lowercase letter, digit, or dash
    sanitized = re.sub(r"[^a-z0-9-]", "", sanitized)

    # Collapse multiple dashes into one
    sanitized = re.sub(r"-+", "-", sanitized)

    # Remove leading/trailing dashes
    sanitized = sanitized.strip("-")

    # Truncate to 128 characters (leaving room for prefix/suffix)
    if len(sanitized) > 100:
        sanitized = sanitized[:100]
        # Make sure we don't end with a dash after truncation
        sanitized = sanitized.rstrip("-")

    # If completely empty after sanitization, use a default
    if not sanitized:
        return "default"

    return sanitized


def get_index_name() -> str:
    """
    Get a valid Azure AI Search index name from configuration.

    Priority:
    1. Derived from PRISM_PROJECT_NAME: prism-{sanitized-project}-index (automatic)
    2. AZURE_SEARCH_INDEX_NAME env var (only if no project specified)
    3. Default: prism-default-index

    The project name is automatically sanitized to meet Azure AI Search naming requirements.

    Returns:
        A valid Azure AI Search index name
    """
    # Priority 1: Derive from project name (automatic per-project isolation)
    project_name = os.getenv("PRISM_PROJECT_NAME")
    if project_name:
        sanitized = sanitize_index_name(project_name)
        index_name = f"prism-{sanitized}-index"
        logger.debug(f"Index name derived from project '{project_name}': {index_name}")
        return index_name

    # Priority 2: Explicit override (only when no project specified)
    explicit_name = os.getenv("AZURE_SEARCH_INDEX_NAME")
    if explicit_name:
        return explicit_name

    return "prism-default-index"


def get_knowledge_source_name() -> str:
    """Get the knowledge source name derived from the index name."""
    return f"{get_index_name()}-source"


def get_knowledge_agent_name() -> str:
    """Get the knowledge agent name derived from the index name."""
    return f"{get_index_name()}-agent"
