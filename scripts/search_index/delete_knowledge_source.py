"""
Delete Azure AI Search Knowledge Source for a project.

This script deletes the knowledge source wrapper around the search index.
The underlying index is NOT deleted - use delete_search_index.py for that.

Naming Convention:
    - Source: prism-{project_name}-index-source

Usage:
    python scripts/search_index/delete_knowledge_source.py

Configuration:
    .env variables:
    - AZURE_SEARCH_ENDPOINT
    - AZURE_SEARCH_ADMIN_KEY
    - PRISM_PROJECT_NAME (used to derive source name)
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


def get_knowledge_source_name() -> str:
    """
    Get knowledge source name from configuration.

    Naming: prism-{project_name}-index-source
    """
    project_name = os.getenv("PRISM_PROJECT_NAME")
    if project_name:
        return f"prism-{project_name}-index-source"

    explicit_name = os.getenv("AZURE_SEARCH_INDEX_NAME")
    if explicit_name:
        return f"{explicit_name}-source"

    return "prism-default-index-source"


def main():
    """Main entry point."""
    source_name = get_knowledge_source_name()

    client = get_index_client()
    if not client:
        return 1

    logger.info(f"Deleting knowledge source '{source_name}'")

    try:
        # Check if knowledge source exists first
        try:
            client.get_knowledge_source(source_name)
        except ResourceNotFoundError:
            logger.warning(f"Knowledge source '{source_name}' does not exist, nothing to delete")
            return 0
        except Exception as e:
            # API might not support get_knowledge_source, try delete anyway
            logger.warning(f"Could not check if source exists: {e}")

        # Delete the knowledge source
        client.delete_knowledge_source(knowledge_source=source_name)
        logger.info(f"Complete: Knowledge source '{source_name}' deleted successfully")
        return 0

    except ResourceNotFoundError:
        logger.warning(f"Knowledge source '{source_name}' does not exist, nothing to delete")
        return 0
    except Exception as e:
        logger.error(f"Failed to delete knowledge source: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
