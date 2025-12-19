"""
Email Processing with Agent-Based Semantic Enhancement.

This module uses a hybrid approach:
1. extract-msg library for reliable extraction (metadata, body, attachments)
2. Agent for semantic enhancement (requirements extraction, categorization, context)

The agent doesn't re-extract (extract-msg is reliable) but adds intelligence and context.
"""

import os
import asyncio
from pathlib import Path
from typing import Dict
from dotenv import load_dotenv

from scripts.logging_config import get_logger
from scripts.azure_credential_helper import get_token_provider

logger = get_logger(__name__)

# Import existing email extraction function
from .extract_msg_files import format_email_as_markdown

from agent_framework import ChatMessage, Role, TextContent
from agent_framework.azure import AzureOpenAIChatClient

# Load environment
load_dotenv()

# Configuration
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
AZURE_OPENAI_CHAT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME", "gpt-5-chat")


def create_email_enhancement_instructions() -> str:
    """Create system instructions for Email Enhancement Agent."""
    return """You are an expert analyst for technical emails and project correspondence.

Your task is to analyze email content that has been reliably extracted and add semantic intelligence.

ANALYSIS TASKS:

## 1. Email Purpose Classification
- Determine email type:
  - Technical Clarification
  - Commercial Query
  - Document Amendment/Addendum
  - Technical Specification
  - Timeline/Schedule Update
  - Meeting Request/Minutes
  - Requirement Clarification
  - Other
- Identify urgency level (urgent, normal, informational)
- Note if response required

## 2. Key Information Extraction
- **Requirements**: Extract any technical or commercial requirements mentioned
- **Specifications**: Identify equipment specs, standards, or technical details
- **Referenced Documents**: List any documents mentioned (specs, drawings, BOQs, etc.)
- **Action Items**: Extract tasks, deliverables, or requests
- **Deadlines**: Note any dates, timelines, or milestones
- **Questions**: List any questions posed that need answers
- **Clarifications**: Note any clarifications or corrections to previous info

## 3. Technical Content Analysis
- **Equipment Mentioned**: List equipment types (transformers, breakers, relays, etc.)
- **Voltage Levels**: Extract voltage levels mentioned (400kV, 132kV, etc.)
- **Standards Referenced**: Note IEC, IEEE, ANSI, BS standards
- **Project References**: Extract project names, locations, phases
- **Parties Involved**: Identify key stakeholders mentioned

## 4. Attachment Analysis
- Categorize attachments by type (specs, drawings, BOQ, etc.)
- Note critical attachments that need processing
- Flag missing expected attachments

## 5. Context and Relationships
- How does this email relate to the project?
- Does it reference other documents or emails?
- What's the impact on requirements or specifications?
- Are there any changes to previously stated requirements?

## 6. Enhanced Markdown Output
- Add executive summary at top
- Structure for clarity with clear sections
- Highlight critical information
- Add context and cross-references
- Include metadata for search optimization

OUTPUT FORMAT:

Provide a JSON response with this structure:

```json
{
  "email_type": "technical_clarification | commercial_query | document_amendment | specification | other",
  "urgency": "urgent | normal | informational",
  "requires_response": true/false,
  "metadata": {
    "equipment_types": ["type1", "type2", ...],
    "voltage_levels": ["400kV", "132kV", ...],
    "standards": ["IEC 62271", ...],
    "project_references": ["Iraq TTC Project", ...],
    "stakeholders": ["Person/Company", ...],
    "referenced_documents": ["Doc1.pdf", "Drawing-X", ...]
  },
  "enhanced_markdown": "The complete enhanced markdown with summary and structure",
  "key_requirements": ["Requirement 1", "Requirement 2", ...],
  "action_items": ["Action 1", "Action 2", ...],
  "questions_posed": ["Question 1", "Question 2", ...],
  "deadlines": ["Deadline 1", "Deadline 2", ...],
  "summary": "Brief executive summary of the email",
  "impact_assessment": "How this email impacts the project",
  "quality_score": 95
}
```

Be thorough and add value through semantic understanding and context."""


# Lazy initialization for Azure OpenAI Client
_client = None
_email_enhancement_agent = None


def _get_client():
    """Lazily initialize the Azure OpenAI client using managed identity."""
    global _client
    if _client is None:
        _client = AzureOpenAIChatClient(
            ad_token_provider=get_token_provider(),
            endpoint=AZURE_OPENAI_ENDPOINT,
            deployment_name=AZURE_OPENAI_CHAT_DEPLOYMENT,
            api_version=AZURE_OPENAI_API_VERSION
        )
    return _client


def _get_email_enhancement_agent():
    """Lazily initialize the Email enhancement agent."""
    global _email_enhancement_agent
    if _email_enhancement_agent is None:
        client = _get_client()
        _email_enhancement_agent = client.create_agent(
            name="Email_Enhancement",
            instructions=create_email_enhancement_instructions()
        )
    return _email_enhancement_agent


async def enhance_email_with_agent(
    msg_path: Path,
    base_markdown: str,
    project_instructions: str = None
) -> Dict:
    """
    Enhance email extraction with semantic analysis using agent.

    Args:
        msg_path: Path to original .msg file
        base_markdown: Markdown representation from extract-msg
        project_instructions: Optional custom instructions from project config

    Returns:
        Enhanced result with metadata and semantic analysis
    """
    # Build analysis request with optional project instructions
    project_context = ""
    if project_instructions:
        project_context = f"""
**Project-Specific Instructions**:
{project_instructions}

"""

    analysis_request = f"""Analyze this technical email and provide semantic enhancement.

**File**: {msg_path.name}
{project_context}
**Extracted Email Content**:

{base_markdown}

Provide comprehensive semantic analysis and enhanced markdown following the instructions."""

    message = ChatMessage(
        role=Role.USER,
        contents=[TextContent(text=analysis_request)]
    )

    try:
        result = await _get_email_enhancement_agent().run(message)
        response_text = result.text

        try:
            json_str = response_text
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()

            import json
            enhancement_data = json.loads(json_str)
            return enhancement_data

        except (json.JSONDecodeError, KeyError, IndexError):
            return {
                "email_type": "unknown",
                "urgency": "normal",
                "requires_response": False,
                "metadata": {},
                "enhanced_markdown": response_text,
                "key_requirements": [],
                "action_items": [],
                "questions_posed": [],
                "deadlines": [],
                "summary": "Email analysis",
                "impact_assessment": "",
                "quality_score": 50
            }

    except Exception as e:
        logger.error(f"Email enhancement failed: {e}")
        return {
            "email_type": "unknown",
            "urgency": "normal",
            "requires_response": False,
            "metadata": {},
            "enhanced_markdown": base_markdown,
            "key_requirements": [],
            "action_items": [],
            "questions_posed": [],
            "deadlines": [],
            "summary": "Email content",
            "impact_assessment": f"Agent enhancement failed: {e}",
            "quality_score": 30
        }


async def process_email_with_agents(msg_path: Path, project_instructions: str = None) -> Dict:
    """
    Process email file with hybrid approach: extract-msg + agent enhancement.

    Args:
        msg_path: Path to .msg file
        project_instructions: Optional custom instructions from project config

    Returns:
        Dict compatible with existing pipeline format
    """
    logger.info(f"Processing Email: {msg_path.name}")

    try:
        base_markdown = format_email_as_markdown(msg_path)

        if not base_markdown:
            raise ValueError("Email extraction failed - no content extracted")

        enhancement = await enhance_email_with_agent(msg_path, base_markdown, project_instructions)

        result = {
            "status": "Succeeded",
            "method": "email_with_agent_enhancement",
            "result": {
                "contents": [{
                    "markdown": enhancement.get('enhanced_markdown', base_markdown)
                }],
                "email_type": enhancement.get('email_type'),
                "urgency": enhancement.get('urgency'),
                "requires_response": enhancement.get('requires_response'),
                "metadata": enhancement.get('metadata', {}),
                "key_requirements": enhancement.get('key_requirements', []),
                "action_items": enhancement.get('action_items', []),
                "questions_posed": enhancement.get('questions_posed', []),
                "deadlines": enhancement.get('deadlines', []),
                "summary": enhancement.get('summary', ''),
                "impact_assessment": enhancement.get('impact_assessment', ''),
                "quality_score": enhancement.get('quality_score', 50)
            }
        }

        logger.info(f"Complete: {msg_path.name} (type: {result['result']['email_type']}, quality: {result['result']['quality_score']})")
        return result

    except Exception as e:
        logger.error(f"Email processing failed: {e}")
        return None


def process_email_with_agents_sync(msg_path: Path, project_instructions: str = None) -> Dict:
    """Synchronous wrapper for async email processing."""
    return asyncio.run(process_email_with_agents(msg_path, project_instructions))
