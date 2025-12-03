"""
Delete Azure AI Search Knowledge Agent for a project.

This script deletes the knowledge agent used for agentic retrieval.
The underlying knowledge source and index are NOT deleted.

Naming Convention:
    - Agent: prism-{project_name}-index-agent

Usage:
    python scripts/search_index/delete_knowledge_agent.py

Configuration:
    .env variables:
    - AZURE_SEARCH_ENDPOINT
    - AZURE_SEARCH_ADMIN_KEY
    - PRISM_PROJECT_NAME (used to derive agent name)
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


def get_knowledge_agent_name() -> str:
    """
    Get knowledge agent name from configuration.

    Naming: prism-{project_name}-index-agent
    """
    project_name = os.getenv("PRISM_PROJECT_NAME")
    if project_name:
        return f"prism-{project_name}-index-agent"

    explicit_name = os.getenv("AZURE_SEARCH_INDEX_NAME")
    if explicit_name:
        return f"{explicit_name}-agent"

    return "prism-default-index-agent"


def main():
    """Main entry point."""
    agent_name = get_knowledge_agent_name()

    client = get_index_client()
    if not client:
        return 1

    logger.info(f"Deleting knowledge agent '{agent_name}'")

    try:
        # Check if agent exists first
        try:
            existing_agents = list(client.list_agents())
            agent_exists = any(a.name == agent_name for a in existing_agents)
            if not agent_exists:
                logger.warning(f"Knowledge agent '{agent_name}' does not exist, nothing to delete")
                return 0
        except Exception as e:
            # API might not support list_agents, try delete anyway
            logger.warning(f"Could not check if agent exists: {e}")

        # Delete the knowledge agent
        client.delete_agent(agent_name)
        logger.info(f"Complete: Knowledge agent '{agent_name}' deleted successfully")
        return 0

    except ResourceNotFoundError:
        logger.warning(f"Knowledge agent '{agent_name}' does not exist, nothing to delete")
        return 0
    except Exception as e:
        logger.error(f"Failed to delete knowledge agent: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
