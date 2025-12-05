"""
Create Azure AI Search Knowledge Source for agentic retrieval.

A knowledge source is a wrapper around your search index that allows
knowledge agents to query it for agentic retrieval workflows.

Naming Convention:
    - Index: prism-{project_name}-index
    - Source: prism-{project_name}-source
    - Agent: prism-{project_name}-agent

Prerequisites:
    - Search index must already exist (run: python main.py index create)
    - Index must have semantic search with default_configuration_name

Usage:
    python scripts/create_knowledge_source.py

Configuration:
    .env variables:
    - AZURE_SEARCH_ENDPOINT
    - AZURE_SEARCH_ADMIN_KEY
    - AZURE_SEARCH_INDEX_NAME (or derived from PRISM_PROJECT_NAME)
    - PRISM_PROJECT_NAME (optional - used to derive names)
    - AZURE_SEARCH_API_VERSION (must be 2025-08-01-preview or later)
"""

import sys
import os
from dotenv import load_dotenv
from scripts.logging_config import get_logger

logger = get_logger(__name__)
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndexKnowledgeSource,
    SearchIndexKnowledgeSourceParameters
)


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


def verify_index_exists(client: SearchIndexClient, index_name: str) -> bool:
    """Verify that the search index exists."""
    try:
        index = client.get_index(index_name)

        if not index.semantic_search:
            logger.error("Index does not have semantic search configured")
            return False

        if not index.semantic_search.default_configuration_name:
            logger.error("Index semantic search missing default_configuration_name")
            return False

        return True

    except Exception as e:
        logger.error(f"Index '{index_name}' not found: {e}")
        return False


def get_index_name() -> str:
    """
    Get index name from configuration.

    Priority:
    1. Derived from PRISM_PROJECT_NAME: prism-{project}-index (automatic)
    2. AZURE_SEARCH_INDEX_NAME env var (only if no project specified)
    3. Default: prism-default-index

    This ensures each project automatically gets its own index without
    requiring manual configuration.
    """
    # Priority 1: Derive from project name (automatic per-project isolation)
    project_name = os.getenv("PRISM_PROJECT_NAME")
    if project_name:
        return f"prism-{project_name}-index"

    # Priority 2: Explicit override (only when no project specified)
    explicit_name = os.getenv("AZURE_SEARCH_INDEX_NAME")
    if explicit_name:
        return explicit_name

    return "prism-default-index"


def main(force: bool = False):
    """Main entry point.

    Args:
        force: If True, automatically recreate existing source without prompting
    """
    index_name = get_index_name()
    knowledge_source_name = f"{index_name}-source"
    api_version = os.getenv("AZURE_SEARCH_API_VERSION", "2025-08-01-preview")

    client = get_index_client()
    if not client:
        return 1

    if not verify_index_exists(client, index_name):
        return 1

    logger.info(f"Creating knowledge source '{knowledge_source_name}'")

    # Check if knowledge source already exists
    try:
        existing_sources = list(client.list_knowledge_sources())
        source_names = [s.name for s in existing_sources]

        if knowledge_source_name in source_names:
            if force:
                logger.info(f"Force mode: Deleting existing source '{knowledge_source_name}'")
                client.delete_knowledge_source(knowledge_source=knowledge_source_name)
            else:
                logger.info(f"Knowledge source '{knowledge_source_name}' already exists (use force=True to recreate)")
                return 0
    except Exception as e:
        logger.warning(f"Could not check existing knowledge sources: {e}")

    # Create knowledge source
    knowledge_source = SearchIndexKnowledgeSource(
        name=knowledge_source_name,
        description=f"Knowledge source for document retrieval from {index_name}",
        search_index_parameters=SearchIndexKnowledgeSourceParameters(
            search_index_name=index_name,
            source_data_select="chunk_id,content,source_file,location,chunk_index"
        )
    )

    try:
        client.create_or_update_knowledge_source(
            knowledge_source=knowledge_source,
            api_version=api_version
        )
        logger.info(f"Complete: Knowledge source '{knowledge_source_name}' created for index '{index_name}'")
    except Exception as e:
        logger.error(f"Failed to create knowledge source: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
