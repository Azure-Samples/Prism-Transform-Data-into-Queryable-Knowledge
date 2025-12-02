"""
Query Service - Handles knowledge agent queries
"""
import os
import sys
from typing import Dict, List, Any, Optional


class QueryService:
    """Service for querying knowledge agent"""

    def __init__(self, base_path: str = None):
        """Initialize query service"""
        if base_path is None:
            base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
        self.base_path = base_path

        # Add base path to sys.path if not already there
        if base_path not in sys.path:
            sys.path.insert(0, base_path)

    async def search_documents(self, query: str, project_id: Optional[str] = None, index_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Search documents using knowledge agent

        Args:
            query: Question to ask
            project_id: Project ID (reads index from project config)
            index_name: Optional index name override (deprecated)

        Returns:
            Dictionary with answer, citations, and query plan
        """
        try:
            # Import the query function
            from scripts.query.query_knowledge_agent import search_documents

            # Set project name so query_knowledge_agent can read from project config
            original_project = os.environ.get('PRISM_PROJECT_NAME')
            if project_id:
                print(f"[QUERY_SERVICE] Setting project from {original_project} to {project_id}")
                os.environ['PRISM_PROJECT_NAME'] = project_id
            elif index_name:
                # Legacy: try to extract project from index name (prism-{project}-index)
                import re
                match = re.match(r'prism-(.+)-index', index_name)
                if match:
                    project_id = match.group(1)
                    print(f"[QUERY_SERVICE] Extracted project '{project_id}' from index name '{index_name}'")
                    os.environ['PRISM_PROJECT_NAME'] = project_id
                else:
                    print(f"[QUERY_SERVICE] Could not extract project from '{index_name}', using as-is")
            else:
                print(f"[QUERY_SERVICE] No project_id provided, using existing: {original_project}")

            try:
                # Execute query
                result = search_documents(query)

                # Parse the response (currently returns a string)
                # In future, modify query_knowledge_agent to return structured data
                return {
                    'query': query,
                    'answer': result,
                    'citations': self._extract_citations(result),
                    'query_plan': None  # Future enhancement
                }

            finally:
                # Restore original project name
                if original_project is not None:
                    os.environ['PRISM_PROJECT_NAME'] = original_project

        except Exception as e:
            print(f"Error querying documents: {e}")
            return {
                'query': query,
                'answer': f"Error: {str(e)}",
                'citations': [],
                'query_plan': None
            }

    def _extract_citations(self, response: str) -> List[Dict[str, Any]]:
        """
        Extract citations from response text

        This is a simple parser. For better results, modify the
        query_knowledge_agent to return structured data.
        """
        citations = []

        # Look for common citation patterns
        # Example: "Attachment 10 (Page 1)"
        import re

        # Pattern: Document name followed by (Page X)
        pattern = r'([A-Za-z0-9\s\-]+?)\s*\(Page\s+(\d+)\)'
        matches = re.findall(pattern, response)

        seen = set()
        for doc_name, page_num in matches:
            doc_name = doc_name.strip()
            key = (doc_name, page_num)
            if key not in seen:
                citations.append({
                    'document': doc_name,
                    'page': int(page_num),
                    'relevance': None  # Would need reranker scores
                })
                seen.add(key)

        return citations
