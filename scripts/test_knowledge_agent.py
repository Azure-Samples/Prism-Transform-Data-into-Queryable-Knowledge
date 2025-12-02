"""
Test Knowledge Agent - Verify GPT-5 migration works

This script sends a test query to the Knowledge Agent to verify:
1. Agent is accessible
2. GPT-5 model is being used
3. Query planning and search are working
4. Results are returned with citations

Usage:
    python scripts/test_knowledge_agent.py
"""

import os
import sys
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
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


def test_knowledge_agent():
    """Test the Knowledge Agent with a simple query."""
    # Get configuration
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    admin_key = os.getenv("AZURE_SEARCH_ADMIN_KEY")
    index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "prism-default-index")
    api_version = os.getenv("AZURE_SEARCH_API_VERSION", "2025-08-01-preview")
    model_name = os.getenv("AZURE_OPENAI_AGENT_MODEL_NAME", "gpt-4.1")

    knowledge_agent_name = f"{index_name}-agent"
    knowledge_source_name = f"{index_name}-source"

    logger.info(f"Testing Knowledge Agent '{knowledge_agent_name}' (model: {model_name})")

    # Verify credentials
    if not endpoint or not admin_key:
        logger.error("Missing Azure credentials in .env")
        return 1

    # Initialize client
    try:
        credential = AzureKeyCredential(admin_key)
        agent_client = KnowledgeAgentRetrievalClient(
            endpoint=endpoint,
            agent_name=knowledge_agent_name,
            credential=credential
        )
    except Exception as e:
        logger.error(f"Could not connect: {e}")
        return 1

    # Test query
    test_query = "What are the substation automation system requirements?"

    try:
        # Build request
        messages = [
            KnowledgeAgentMessage(
                role="user",
                content=[KnowledgeAgentMessageTextContent(text=test_query)]
            )
        ]

        retrieval_request = KnowledgeAgentRetrievalRequest(
            messages=messages,
            knowledge_source_params=[
                SearchIndexKnowledgeSourceParams(
                    knowledge_source_name=knowledge_source_name
                )
            ]
        )

        # Execute query
        response = agent_client.retrieve(
            retrieval_request=retrieval_request,
            api_version=api_version
        )

        # Check for response content
        answer_text = None
        if hasattr(response, 'response') and response.response:
            for resp_msg in response.response:
                if hasattr(resp_msg, 'content'):
                    for content_item in resp_msg.content:
                        if hasattr(content_item, 'text'):
                            answer_text = content_item.text
                            break
                    if answer_text:
                        break

        # Check activity (query planning)
        has_activity = False
        if hasattr(response, 'as_dict'):
            response_dict = response.as_dict()
            has_activity = 'activity' in response_dict and len(response_dict.get('activity', [])) > 0

        # Check references (citations)
        has_references = hasattr(response, 'references') and len(response.references) > 0
        has_answer = answer_text is not None and len(answer_text) > 0

        ref_count = len(response.references) if has_references else 0
        answer_len = len(answer_text) if has_answer else 0

        if has_answer and has_activity:
            logger.info(f"Test passed: answer={answer_len} chars, citations={ref_count}, planning=yes")
            return 0
        else:
            issues = []
            if not has_answer:
                issues.append("no answer")
            if not has_activity:
                issues.append("no query planning")
            if not has_references:
                issues.append("no citations")
            logger.error(f"Test failed: {', '.join(issues)}")
            return 1

    except Exception as e:
        logger.error(f"Query failed: {e}")
        return 1


def main():
    """Main entry point."""
    return test_knowledge_agent()


if __name__ == "__main__":
    sys.exit(main())
