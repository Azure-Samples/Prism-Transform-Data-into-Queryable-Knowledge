"""
Chat Service - Handles contextual chat with document search
"""
import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

from apps.api.app.services.storage_service import get_storage_service


class ChatService:
    """Service for contextual chat with document search"""

    def __init__(self, base_path: str = None):
        """Initialize chat service"""
        if base_path is None:
            base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
        self.base_path = base_path

        # Add base path to sys.path if not already there
        if base_path not in sys.path:
            sys.path.insert(0, base_path)

    async def chat(
        self,
        project_id: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Process a chat message with optional context

        Args:
            project_id: Project ID for document search
            message: User's message
            context: Optional context (question/answer being discussed)
            conversation_history: Previous messages in the conversation

        Returns:
            Dictionary with message and citations
        """
        try:
            from scripts.query.query_knowledge_agent import search_documents

            # Set project for search
            original_project = os.environ.get('PRISM_PROJECT_NAME')
            os.environ['PRISM_PROJECT_NAME'] = project_id

            try:
                # Build the search query with context
                search_query = self._build_contextual_query(message, context, conversation_history)

                # Search documents
                result = search_documents(search_query)

                # Parse response
                return {
                    'message': result,
                    'citations': self._extract_citations(result)
                }

            finally:
                # Restore original project
                if original_project is not None:
                    os.environ['PRISM_PROJECT_NAME'] = original_project
                elif 'PRISM_PROJECT_NAME' in os.environ:
                    del os.environ['PRISM_PROJECT_NAME']

        except Exception as e:
            print(f"[CHAT_SERVICE] Error: {e}")
            return {
                'message': f"Error processing your request: {str(e)}",
                'citations': []
            }

    def _build_contextual_query(
        self,
        message: str,
        context: Optional[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]]
    ) -> str:
        """
        Build a search query that incorporates context

        Args:
            message: User's current message
            context: Question context if any
            conversation_history: Previous messages

        Returns:
            Enhanced query string
        """
        query_parts = []

        # Add context if we're discussing a specific question
        if context and context.get('question_text'):
            query_parts.append(f"Context - Original Question: {context['question_text']}")

            if context.get('current_answer'):
                query_parts.append(f"Current Answer: {context['current_answer']}")

            if context.get('current_reference'):
                query_parts.append(f"Current Reference: {context['current_reference']}")

            query_parts.append("---")

        # Add relevant conversation history (last 2 exchanges max to avoid token limits)
        if conversation_history and len(conversation_history) > 0:
            recent_history = conversation_history[-4:]  # Last 2 user + 2 assistant messages
            for msg in recent_history:
                role = msg.get('role', 'user')
                content = msg.get('content', '')[:200]  # Truncate long messages
                if role == 'user':
                    query_parts.append(f"Previous question: {content}")
                else:
                    query_parts.append(f"Previous answer summary: {content[:100]}...")

            query_parts.append("---")

        # Add the current message
        query_parts.append(f"Current question: {message}")

        return "\n".join(query_parts)

    def _extract_citations(self, response: str) -> List[Dict[str, Any]]:
        """Extract citations from response text"""
        import re
        citations = []
        seen = set()

        # Pattern: Document name followed by (Page X)
        pattern = r'([A-Za-z0-9\s\-_\.]+?)\s*\(Page\s+(\d+)\)'
        matches = re.findall(pattern, response)

        for doc_name, page_num in matches:
            doc_name = doc_name.strip()
            key = (doc_name, page_num)
            if key not in seen and len(doc_name) > 2:
                citations.append({
                    'document': doc_name,
                    'page': int(page_num),
                    'relevance': None
                })
                seen.add(key)

        return citations

    async def update_result(
        self,
        project_id: str,
        section_id: str,
        question_id: str,
        new_answer: Optional[str] = None,
        new_reference: Optional[str] = None,
        new_comments: Optional[str] = None
    ) -> bool:
        """
        Update a result in the project's results.json (blob storage)

        Args:
            project_id: Project ID
            section_id: Section ID
            question_id: Question ID
            new_answer: New answer text (if provided)
            new_reference: New reference text (if provided)
            new_comments: New comments text (if provided)

        Returns:
            True if updated successfully
        """
        try:
            storage = get_storage_service()
            results = storage.read_json(project_id, "output/results.json")

            if not results:
                return False

            # Navigate to the question
            sections = results.get('sections', {})
            if section_id not in sections:
                return False

            questions = sections[section_id].get('questions', {})
            if question_id not in questions:
                return False

            # Update fields if provided
            if new_answer is not None:
                questions[question_id]['answer'] = new_answer
            if new_reference is not None:
                questions[question_id]['reference'] = new_reference
            if new_comments is not None:
                questions[question_id]['comments'] = new_comments

            # Save back to blob storage
            storage.write_json(project_id, "output/results.json", results)

            return True

        except Exception as e:
            print(f"[CHAT_SERVICE] Error updating result: {e}")
            return False
