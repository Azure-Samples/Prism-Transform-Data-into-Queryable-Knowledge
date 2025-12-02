"""
Delete Azure AI Search Knowledge Agent and Knowledge Source.

Usage:
    python scripts/search_index/delete_knowledge_agent_and_source.py

This will delete the agent and source for the index specified in .env AZURE_SEARCH_INDEX_NAME.
"""

import sys
import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from scripts.logging_config import get_logger

logger = get_logger(__name__)

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


def main():
    """Main entry point."""
    index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "prism-default-index")
    knowledge_source_name = f"{index_name}-source"
    knowledge_agent_name = f"{index_name}-agent"

    client = get_index_client()
    if not client:
        return 1

    logger.info(f"Deleting agent '{knowledge_agent_name}' and source '{knowledge_source_name}'")

    agent_deleted = False
    source_deleted = False

    try:
        client.delete_agent(knowledge_agent_name)
        agent_deleted = True
    except Exception as e:
        logger.warning(f"Could not delete agent: {e}")

    try:
        client.delete_knowledge_source(knowledge_source_name)
        source_deleted = True
    except Exception as e:
        logger.warning(f"Could not delete source: {e}")

    logger.info(f"Complete: agent={'deleted' if agent_deleted else 'skipped'}, source={'deleted' if source_deleted else 'skipped'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
