"""
Knowledge Agent Query Module.

This module provides document search functionality using Azure AI Search Knowledge Agent.
Used by the API services (query_service.py, chat_service.py) for document retrieval.

Naming Convention:
    - Index: prism-{project_name}-index
    - Source: prism-{project_name}-source
    - Agent: prism-{project_name}-agent

Primary function:
    search_documents(query: str) -> str: Search documents and return formatted answer with citations
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.agent import KnowledgeAgentRetrievalClient
from azure.search.documents.agent.models import (
    KnowledgeAgentRetrievalRequest,
    KnowledgeAgentMessage,
    KnowledgeAgentMessageTextContent,
    SearchIndexKnowledgeSourceParams
)

from scripts.logging_config import get_logger

logger = get_logger(__name__)

# Load environment
load_dotenv()


# Configuration
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_ADMIN_KEY = os.getenv("AZURE_SEARCH_ADMIN_KEY")
AZURE_SEARCH_API_VERSION = os.getenv("AZURE_SEARCH_API_VERSION", "2025-08-01-preview")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
AZURE_OPENAI_CHAT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME", "gpt-5-chat")


def get_index_name() -> str:
    """
    Get index name from configuration.

    Priority:
    1. Derived from PRISM_PROJECT_NAME: prism-{project}-index (automatic)
    2. AZURE_SEARCH_INDEX_NAME env var (only if no project specified)
    3. Default: prism-default-index

    This ensures each project automatically gets its own index without
    requiring manual configuration. No need to hardcode index names in config.json.
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


# Dynamic index/agent/source names
AZURE_SEARCH_INDEX_NAME = get_index_name()
KNOWLEDGE_AGENT_NAME = f"{AZURE_SEARCH_INDEX_NAME}-agent"
KNOWLEDGE_SOURCE_NAME = f"{AZURE_SEARCH_INDEX_NAME}-source"

def _get_chunk_metadata(chunk_id: str) -> dict:
    """
    Get metadata for a chunk by fetching from Azure AI Search index.

    Args:
        chunk_id: The chunk ID (e.g., 'd11f08a1_chunk_014')

    Returns:
        dict with 'source_file' and 'location'
    """
    try:
        # Use shared get_index_name() to respect PRISM_PROJECT_NAME (DRY principle)
        index_name = get_index_name()

        # Initialize search client
        credential = AzureKeyCredential(AZURE_SEARCH_ADMIN_KEY)
        search_client = SearchClient(
            endpoint=AZURE_SEARCH_ENDPOINT,
            index_name=index_name,
            credential=credential
        )

        # Fetch the document by chunk_id
        doc = search_client.get_document(key=chunk_id, selected_fields=["source_file", "location"])

        return {
            'source_file': doc.get('source_file', 'Unknown'),
            'location': doc.get('location')
        }
    except Exception as e:
        logger.debug(f"Could not fetch metadata for {chunk_id}: {e}")
        return {}


def search_documents(query: str) -> str:
    """
    Search documents using Azure AI Search Knowledge Agent with smart retry logic.

    This function is called by the chat agent as a tool when the user asks questions.
    It uses agentic retrieval with query planning, parallel search, and answer synthesis.

    SMART RETRY LOGIC:
    - Attempt 1: Original query
    - Attempt 2: Simplified query (if no results)
    - Attempt 3: Expanded query with synonyms (if still no results)

    Each query is independent - no conversation history is maintained to avoid token limits and crashes.

    Args:
        query: The user's question about the indexed documents

    Returns:
        AI-generated answer with citations from the knowledge store
    """
    # Attempt 1: Original query
    result = _perform_search(query, attempt=0, inference_keywords=[])

    # Check if we got meaningful results
    if "No relevant content was found" in result.get('response', ''):
        logger.debug(f"No results for original query: '{query}'")

        # Attempt 2: Simplified query (remove acronyms, focus on core terms)
        simplified = _simplify_query(query)
        if simplified != query:
            logger.debug(f"Trying simplified query: '{simplified}'")
            result = _perform_search(simplified, attempt=1, inference_keywords=[])

        # Attempt 3: Expanded query (add synonyms)
        if "No relevant content was found" in result.get('response', ''):
            expanded = _expand_query(query)
            if expanded != query:
                logger.debug(f"Trying expanded query: '{expanded}'")
                result = _perform_search(expanded, attempt=2, inference_keywords=[])

    # Return the response
    return result.get('response', 'Information not found in the available documents.')


def _simplify_query(query: str) -> str:
    """
    Simplify query by removing specific acronyms/modifiers to broaden search.

    Examples:
        "OSS Wind Farm SCADA" → "SCADA system"
        "HVDC SCADA interface" → "SCADA interface"
        "132kV substation automation" → "substation automation"
    """
    # Extract core technical terms
    keywords = {
        'SCADA': 'SCADA system',
        'substation': 'substation',
        'automation': 'automation system',
        'control': 'control system',
        'protection': 'protection system',
        'monitoring': 'monitoring system',
        'RTU': 'remote terminal unit'
    }

    query_lower = query.lower()
    for keyword, replacement in keywords.items():
        if keyword.lower() in query_lower:
            return replacement

    # Fallback: return original
    return query


def _expand_query(query: str) -> str:
    """
    Expand query with OR synonyms to broaden search.

    Examples:
        "OSS SCADA" → "OSS SCADA OR offshore substation control OR monitoring system"
        "automation system" → "automation system OR SCADA OR control system"
    """
    # Add context-specific synonyms
    if "SCADA" in query:
        return f"{query} OR substation control system OR monitoring system OR supervisory control"
    elif "automation" in query:
        return f"{query} OR control system OR SCADA OR monitoring"
    elif "protection" in query:
        return f"{query} OR relay system OR protective device OR safety system"
    elif "substation" in query and "automation" not in query:
        return f"{query} OR substation automation OR substation control"

    # Fallback: add generic broadening
    return f"{query} OR control OR monitoring OR system"



def _perform_search(query: str, attempt: int, inference_keywords: list) -> dict:
    """
    Internal function to perform a single search attempt.
    Each search is independent with no conversation history.

    Args:
        query: The search query
        attempt: Attempt number (not used, kept for compatibility)
        inference_keywords: List of words that indicate hallucination (not used, kept for compatibility)

    Returns:
        dict with 'response' key
    """
    try:
        # Get current index name dynamically (reads from project config or env var)
        index_name = get_index_name()
        agent_name = f"{index_name}-agent"
        source_name = f"{index_name}-source"

        logger.debug(f"Using index: {index_name}, agent: {agent_name}, source: {source_name}")

        # Initialize Knowledge Agent Retrieval Client
        credential = AzureKeyCredential(AZURE_SEARCH_ADMIN_KEY)
        agent_client = KnowledgeAgentRetrievalClient(
            endpoint=AZURE_SEARCH_ENDPOINT,
            agent_name=agent_name,
            credential=credential
        )

        # Build messages array with system instructions + conversation history + current query
        messages = []

        # 1. Add system instructions to guide the Knowledge Agent's behavior
        system_instructions = """You are a document retrieval assistant for answering questions based on indexed documents.

STRICT GROUNDING RULES - YOU MUST FOLLOW THESE:
1. ONLY answer using information EXPLICITLY STATED in the retrieved documents
2. NEVER use general knowledge or make inferences beyond what the documents state
3. ALWAYS cite specific documents and page/section numbers for every factual claim
4. If information is NOT in the documents, respond: "This information is not found in the available documents"
5. If information is uncertain or conflicting, respond: "UNCERTAIN: [explain the conflict or ambiguity]"
6. Do NOT make assumptions about typical practices, standard configurations, or common requirements
7. Do NOT infer requirements from related mentions

DISTINGUISHING "NOT FOUND" vs "EXPLICITLY EXCLUDED":
- "NOT FOUND": No mention in documents → Answer: "Information not found in available documents"
- "EXPLICITLY EXCLUDED": Document states "not required" or "excluded" → Answer with citation

ALLOWED MARKED ASSUMPTIONS (only when necessary):
- If you must make a reasonable inference, CLEARLY mark it: "ASSUMPTION: [explain reasoning]"
- Assumptions should be based on explicit document context, not general knowledge
- Always prefer "Information not found" over making assumptions

When providing details:
- Extract exact values, standards, and specifications as written in documents
- Use direct quotes where possible to ensure accuracy
- Cite document name and page/section for each specification
- If a detail is partially found, state what IS found and what is MISSING
"""

        messages.append(
            KnowledgeAgentMessage(
                role="system",
                content=[KnowledgeAgentMessageTextContent(text=system_instructions)]
            )
        )

        # 2. Add current user query (no conversation history to avoid token limits)
        messages.append(
            KnowledgeAgentMessage(
                role="user",
                content=[KnowledgeAgentMessageTextContent(text=query)]
            )
        )

        # Create retrieval request with system instructions + conversation history + current query
        retrieval_request = KnowledgeAgentRetrievalRequest(
            messages=messages,  # Includes: system instructions, conversation history, current query
            knowledge_source_params=[
                SearchIndexKnowledgeSourceParams(
                    knowledge_source_name=source_name,
                    always_query_source=True  # IMPROVED: Always query, never rely on LLM training data
                )
            ],
            max_runtime_in_seconds=120  # IMPROVED: Extended runtime for retries
        )

        # Query the knowledge agent
        # The Knowledge Agent will:
        # 1. Use system instructions to understand its role and constraints
        # 2. Break down complex queries into focused subqueries
        # 3. Run parallel searches against the knowledge source with semantic reranking
        # 4. Synthesize an answer with citations based on the system instructions
        response = agent_client.retrieve(
            retrieval_request=retrieval_request,
            api_version=AZURE_SEARCH_API_VERSION
        )

        logger.debug(f"Query sent to Knowledge Agent")

        # Extract answer text from response
        answer_text = None
        if hasattr(response, 'response') and response.response:
            # Response is in response.response (list of messages)
            for resp_msg in response.response:
                if hasattr(resp_msg, 'content'):
                    for content_item in resp_msg.content:
                        if hasattr(content_item, 'text'):
                            answer_text = content_item.text
                            break
                    if answer_text:
                        break

        if answer_text:

            # Extract references from Knowledge Agent
            has_references = hasattr(response, 'references') and response.references
            citations_text = "\n\n=== SOURCE DOCUMENTS ===\n"
            if has_references:
                # Track unique source files to avoid duplicate citations
                seen_sources = {}
                citation_num = 1

                for ref in response.references:
                    ref_dict = ref.as_dict() if hasattr(ref, 'as_dict') else ref

                    # Extract document info
                    doc_key = ref_dict.get('doc_key', 'Unknown')  # This is the chunk_id
                    reranker_score = ref_dict.get('reranker_score', 0)
                    activity_source = ref_dict.get('activity_source', 'N/A')

                    # Try to get source_file from the reference
                    # The doc_key is the chunk_id, need to look it up
                    source_file = None
                    location = None

                    # If we have access to the document content from search results
                    if 'content' in ref_dict:
                        # Extract source_file and location if available in content
                        content_doc = ref_dict.get('content', {})
                        if isinstance(content_doc, dict):
                            source_file = content_doc.get('source_file')
                            location = content_doc.get('location')

                    # Fallback: try to extract from doc_key field itself
                    if not source_file and 'source_file' in ref_dict:
                        source_file = ref_dict.get('source_file')
                        location = ref_dict.get('location')

                    # Last resort: lookup from chunk metadata cache
                    if not source_file and doc_key and doc_key != 'Unknown':
                        chunk_meta = _get_chunk_metadata(doc_key)
                        source_file = chunk_meta.get('source_file')
                        location = chunk_meta.get('location')

                    # Create a readable citation
                    if source_file:
                        doc_citation = source_file
                        if location:
                            doc_citation += f" ({location})"

                        # Only add if we haven't seen this source yet
                        if doc_citation not in seen_sources:
                            seen_sources[doc_citation] = reranker_score
                            citations_text += f"\n{citation_num}. {doc_citation}\n"
                            citations_text += f"   Relevance: {reranker_score:.2f}\n"
                            citation_num += 1
                    else:
                        # Fallback to chunk_id if source_file not available
                        citations_text += f"\n{citation_num}. Chunk: {doc_key}\n"
                        citations_text += f"   Relevance: {reranker_score:.2f}\n"
                        citation_num += 1
            else:
                citations_text += "\n⚠️ NO REFERENCES FOUND\n"

            # Show query planning activity
            if hasattr(response, 'activity') and response.activity:
                citations_text += "\n=== QUERY PLANNING ===\n"
                for act in response.activity:
                    act_dict = act.as_dict() if hasattr(act, 'as_dict') else act
                    act_type = act_dict.get('type', 'unknown')
                    if act_type == 'searchIndex':
                        search_args = act_dict.get('search_index_arguments', {})
                        search_query = search_args.get('search', 'N/A')
                        count = act_dict.get('count', 0)
                        citations_text += f"\n  Subquery: \"{search_query}\" → {count} results\n"

            full_response = answer_text + citations_text

            # No conversation history - each query is independent to avoid token limits and crashes

            return {'response': full_response}
        else:
            logger.debug(f"Could not extract answer from response")
            return {'response': f"I received a response but couldn't parse it. Response: {str(response)[:500]}"}

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Knowledge agent search failed for query '{query[:50]}...': {e}")
        return {'response': f"Error querying knowledge agent: {e}\n\nDetails:\n{error_details}"}


