"""
Create Azure AI Search index for Prism knowledge store.

This script creates a search index optimized for hybrid search (vector + keyword)
with semantic ranker for improved relevance.

Index Schema:
    - chunk_id (key): Unique identifier
    - content (searchable): Markdown content
    - content_vector (vector): 1024-dimensional embedding
    - source_file (filterable): Original document filename
    - location (filterable): Document location (Page N, Sheet: Name, etc.)
    - chunk_index (sortable): Position in document

Naming Convention:
    - Index: prism-{project_name}-index
    - Source: prism-{project_name}-source (created separately)
    - Agent: prism-{project_name}-agent (created separately)

Usage:
    python scripts/create_search_index.py

Configuration:
    .env variables:
    - AZURE_SEARCH_ENDPOINT
    - AZURE_SEARCH_ADMIN_KEY
    - AZURE_SEARCH_INDEX_NAME (or derived from PRISM_PROJECT_NAME)
    - PRISM_PROJECT_NAME (optional - used to derive index name)
"""

import sys
import os
from dotenv import load_dotenv
from scripts.logging_config import get_logger

logger = get_logger(__name__)
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters,
    ScoringProfile,
    TextWeights,
    SearchIndexerDataNoneIdentity  # For system-assigned managed identity
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


def create_index_definition(index_name: str, vector_dimensions: int = 1024) -> SearchIndex:
    """
    Create index definition with vector search and semantic ranking.

    Args:
        index_name: Name of the index
        vector_dimensions: Embedding dimensions (1024 for text-embedding-3-large)

    Returns:
        SearchIndex definition
    """

    # Define fields
    fields = [
        # Key field
        SimpleField(
            name="chunk_id",
            type=SearchFieldDataType.String,
            key=True,
            sortable=True,
            filterable=True
        ),

        # Content field (searchable text)
        SearchableField(
            name="content",
            type=SearchFieldDataType.String,
            searchable=True,
            analyzer_name="standard.lucene"
        ),

        # Vector field (embeddings)
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=vector_dimensions,
            vector_search_profile_name="prism-vector-profile"
        ),

        # Metadata fields (must be retrievable for citations)
        SimpleField(
            name="source_file",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
            retrievable=True  # CRITICAL: Must be retrievable for Knowledge Agent citations
        ),

        # Location field - "Page 1", "Sheet: Sales", "Email Body", etc.
        SearchableField(
            name="location",
            type=SearchFieldDataType.String,
            filterable=True,
            sortable=True,
            retrievable=True  # CRITICAL: Must be retrievable for Knowledge Agent citations
        ),

        SimpleField(
            name="chunk_index",
            type=SearchFieldDataType.Int32,
            sortable=True,
            retrievable=True
        )
    ]

    # Get Azure OpenAI embedding configuration
    aoai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    aoai_embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME", "text-embedding-3-large")
    aoai_embedding_model = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL_NAME", "text-embedding-3-large")

    # Note: The vectorizer configuration stored in Azure Search requires either:
    # 1. API key (if key-based auth is enabled on Azure OpenAI)
    # 2. Managed identity (Azure Search system identity with RBAC on Azure OpenAI)
    #
    # We prefer managed identity but fall back to API key if available.
    # For managed identity: Azure Search service must have system-assigned identity
    # with "Cognitive Services OpenAI User" role on the Azure OpenAI resource.
    aoai_api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_KEY")

    # Configure Azure OpenAI Vectorizer for query embeddings
    # If no API key, use Search service's system-assigned managed identity
    if aoai_api_key:
        vectorizer_params = AzureOpenAIVectorizerParameters(
            resource_url=aoai_endpoint,
            api_key=aoai_api_key,
            deployment_name=aoai_embedding_deployment,
            model_name=aoai_embedding_model
        )
    else:
        # Use system-assigned managed identity (SearchIndexerDataNoneIdentity)
        # Azure Search service must have "Cognitive Services OpenAI User" role on Azure OpenAI
        vectorizer_params = AzureOpenAIVectorizerParameters(
            resource_url=aoai_endpoint,
            deployment_name=aoai_embedding_deployment,
            model_name=aoai_embedding_model,
            auth_identity=SearchIndexerDataNoneIdentity()
        )
        logger.info("No API key provided - Azure Search will use its managed identity for vectorization")

    vectorizer = AzureOpenAIVectorizer(
        vectorizer_name="prism-aoai-vectorizer",
        parameters=vectorizer_params
    )

    # Configure vector search (HNSW algorithm)
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="prism-hnsw-config",
                parameters={
                    "m": 4,  # Number of bi-directional links (default: 4)
                    "efConstruction": 400,  # Size of dynamic candidate list (default: 400)
                    "efSearch": 500,  # Size of candidate list for search (default: 500)
                    "metric": "cosine"  # Distance metric
                }
            )
        ],
        profiles=[
            VectorSearchProfile(
                name="prism-vector-profile",
                algorithm_configuration_name="prism-hnsw-config",
                vectorizer_name="prism-aoai-vectorizer"  # Link to vectorizer
            )
        ],
        vectorizers=[vectorizer]  # Add vectorizer configuration
    )

    # Configure semantic search (REQUIRED for agentic retrieval)
    semantic_config = SemanticConfiguration(
        name="prism-semantic-config",
        prioritized_fields=SemanticPrioritizedFields(
            content_fields=[SemanticField(field_name="content")]
        )
    )

    semantic_search = SemanticSearch(
        default_configuration_name="prism-semantic-config",  # Required for agentic retrieval
        configurations=[semantic_config]
    )

    # Configure scoring profile (REQUIRED for Knowledge Agents!)
    scoring_profile = ScoringProfile(
        name="prism-default-scoring",
        text_weights=TextWeights(
            weights={"content": 1.0}  # Boost content field
        )
    )

    # Create index definition
    index = SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search,
        scoring_profiles=[scoring_profile],
        default_scoring_profile="prism-default-scoring"  # Set as default
    )

    return index


# Import shared index naming utility (handles sanitization for Azure Search requirements)
from scripts.search_index.index_utils import get_index_name


def main(force: bool = False):
    """
    Main entry point.

    Args:
        force: If True, delete and recreate existing index. If False, skip if exists.
    """
    index_name = get_index_name()
    dimensions = int(os.getenv("AZURE_OPENAI_EMBEDDING_DIMENSIONS", "1024"))

    client = get_index_client()
    if not client:
        return 1

    logger.info(f"Creating index '{index_name}' ({dimensions} dimensions)")

    # Check if index already exists
    try:
        existing_indexes = [idx.name for idx in client.list_indexes()]
        if index_name in existing_indexes:
            if force:
                logger.info(f"Index '{index_name}' exists, deleting...")
                client.delete_index(index_name)
            else:
                logger.info(f"Index '{index_name}' already exists, skipping")
                return 0
    except Exception as e:
        logger.warning(f"Could not check existing indexes: {e}")

    # Create index
    index = create_index_definition(index_name, dimensions)

    try:
        client.create_index(index)
        created_index = client.get_index(index_name)
        logger.info(f"Complete: Index '{index_name}' created with {len(created_index.fields)} fields")
    except Exception as e:
        logger.error(f"Failed to create index: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
