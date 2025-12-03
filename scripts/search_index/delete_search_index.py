"""
Delete Azure AI Search index for a project.

This script deletes the search index and all documents within it.
Use with caution - this operation is irreversible.

Naming Convention:
    - Index: prism-{project_name}-index

Usage:
    python scripts/search_index/delete_search_index.py

Configuration:
    .env variables:
    - AZURE_SEARCH_ENDPOINT
    - AZURE_SEARCH_ADMIN_KEY
    - PRISM_PROJECT_NAME (used to derive index name)
"""

import sys
import os
from dotenv import load_dotenv
from scripts.logging_config import get_logger

logger = get_logger(__name__)
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.core.exceptions import ResourceNotFoundError


# Load environment variables
load_dotenv()


def get_index_client() -> SearchIndexClient:
    """Initialize Azure AI Search index client."""
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    admin_key = os.getenv("AZURE_SEARCH_ADMIN_KEY")

    if not endpoint or not admin_key:
        logger.error("Azure AI Search credentials not found in .env")
        return None

    credential = AzureKeyCredential(admin_key)
    client = SearchIndexClient(endpoint=endpoint, credential=credential)

    return client


def get_index_name() -> str:
    """
    Get index name from configuration.

    Priority:
    1. Derived from PRISM_PROJECT_NAME: prism-{project}-index (automatic)
    2. AZURE_SEARCH_INDEX_NAME env var (only if no project specified)
    3. Default: prism-default-index
    """
    project_name = os.getenv("PRISM_PROJECT_NAME")
    if project_name:
        return f"prism-{project_name}-index"

    explicit_name = os.getenv("AZURE_SEARCH_INDEX_NAME")
    if explicit_name:
        return explicit_name

    return "prism-default-index"


def main():
    """Main entry point."""
    index_name = get_index_name()

    client = get_index_client()
    if not client:
        return 1

    logger.info(f"Deleting index '{index_name}'")

    try:
        # Check if index exists first
        try:
            client.get_index(index_name)
        except ResourceNotFoundError:
            logger.warning(f"Index '{index_name}' does not exist, nothing to delete")
            return 0

        # Delete the index
        client.delete_index(index_name)
        logger.info(f"Complete: Index '{index_name}' deleted successfully")
        return 0

    except Exception as e:
        logger.error(f"Failed to delete index: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
