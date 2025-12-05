"""
Create Azure AI Search Knowledge Agent for agentic retrieval.

A knowledge agent orchestrates query planning, execution, and answer synthesis
for agentic retrieval workflows. It uses an LLM to break down complex queries,
runs parallel searches, and synthesizes answers with citations.

Naming Convention:
    - Index: prism-{project_name}-index
    - Source: prism-{project_name}-source
    - Agent: prism-{project_name}-agent

Prerequisites:
    - Knowledge source must already exist (run: python main.py source create)
    - Azure OpenAI chat model deployed (gpt-4o, gpt-4.1, or gpt-5 series)

Usage:
    python scripts/create_knowledge_agent.py

Configuration:
    .env variables:
    - AZURE_SEARCH_ENDPOINT
    - AZURE_SEARCH_ADMIN_KEY
    - AZURE_SEARCH_INDEX_NAME (or derived from PRISM_PROJECT_NAME)
    - PRISM_PROJECT_NAME (optional - used to derive names)
    - AZURE_SEARCH_API_VERSION (must be 2025-08-01-preview or later)
    - AZURE_OPENAI_ENDPOINT
    - AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
    - AZURE_OPENAI_AGENT_MODEL_NAME (exact model: gpt-5, gpt-4o, etc. - not deployment name)
"""

import sys
import os
import json
from dotenv import load_dotenv
from scripts.logging_config import get_logger

logger = get_logger(__name__)
from apps.api.app.services.storage_service import get_storage_service
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    KnowledgeAgent,
    KnowledgeAgentAzureOpenAIModel,
    KnowledgeSourceReference,
    AzureOpenAIVectorizerParameters,
    KnowledgeAgentOutputConfiguration,
    KnowledgeAgentOutputConfigurationModality
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


def verify_knowledge_source_exists(client: SearchIndexClient, source_name: str) -> bool:
    """Verify that the knowledge source exists."""
    try:
        client.get_knowledge_source(source_name)
        return True
    except Exception as e:
        logger.error(f"Knowledge source '{source_name}' not found: {e}")
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


def _update_project_config(agent_name: str):
    """Update project config to mark agent as created."""
    project_name = os.getenv("PRISM_PROJECT_NAME")
    if project_name:
        try:
            storage = get_storage_service()
            config = storage.read_json(project_name, "config.json")
            if config:
                if 'status' not in config:
                    config['status'] = {}
                config['status']['has_agent'] = True
                config['status']['agent_name'] = agent_name
                storage.write_json(project_name, "config.json", config)
        except Exception as e:
            logger.warning(f"Could not update project status: {e}")


def main(force: bool = False):
    """Main entry point.

    Args:
        force: If True, automatically recreate existing agent without prompting
    """
    index_name = get_index_name()
    knowledge_source_name = f"{index_name}-source"
    knowledge_agent_name = f"{index_name}-agent"
    api_version = os.getenv("AZURE_SEARCH_API_VERSION", "2025-08-01-preview")

    # Azure OpenAI configuration
    aoai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    aoai_api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_KEY")
    aoai_chat_deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
    aoai_agent_model = os.getenv("AZURE_OPENAI_AGENT_MODEL_NAME", "gpt-4.1")

    if not aoai_endpoint or not aoai_chat_deployment or not aoai_api_key:
        logger.error("Azure OpenAI configuration not found in .env")
        return 1

    client = get_index_client()
    if not client:
        return 1

    if not verify_knowledge_source_exists(client, knowledge_source_name):
        return 1

    logger.info(f"Creating knowledge agent '{knowledge_agent_name}'")

    # Check if agent already exists
    try:
        existing_agents = list(client.list_agents())
        agent_names = [a.name for a in existing_agents]

        if knowledge_agent_name in agent_names:
            if force:
                logger.info(f"Force mode: Deleting existing agent '{knowledge_agent_name}'")
                client.delete_agent(knowledge_agent_name)
            else:
                logger.info(f"Knowledge agent '{knowledge_agent_name}' already exists (use force=True to recreate)")
                # Still update config to mark agent as existing
                _update_project_config(knowledge_agent_name)
                return 0
    except Exception as e:
        logger.warning(f"Could not check existing agents: {e}")

    # Create knowledge agent
    aoai_params = AzureOpenAIVectorizerParameters(
        resource_url=aoai_endpoint,
        api_key=aoai_api_key,
        deployment_name=aoai_chat_deployment,
        model_name=aoai_agent_model
    )

    output_config = KnowledgeAgentOutputConfiguration(
        modality=KnowledgeAgentOutputConfigurationModality.ANSWER_SYNTHESIS,
        include_activity=True
    )

    agent = KnowledgeAgent(
        name=knowledge_agent_name,
        description="Knowledge agent for document retrieval and answer synthesis",
        models=[KnowledgeAgentAzureOpenAIModel(azure_open_ai_parameters=aoai_params)],
        knowledge_sources=[
            KnowledgeSourceReference(
                name=knowledge_source_name,
                reranker_threshold=2.0
            )
        ],
        output_configuration=output_config
    )

    try:
        client.create_or_update_agent(agent=agent, api_version=api_version)
        logger.info(f"Complete: Knowledge agent '{knowledge_agent_name}' created (model: {aoai_agent_model})")
        _update_project_config(knowledge_agent_name)

    except Exception as e:
        logger.error(f"Failed to create knowledge agent: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
