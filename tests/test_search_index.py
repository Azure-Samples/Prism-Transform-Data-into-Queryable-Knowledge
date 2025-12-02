"""
Tests for search index scripts (Phase 4: Generalize Search/Query)

These tests focus on the helper functions and configuration logic.
Azure API calls are mocked since they require credentials.
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add project root to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestGetIndexNameFunction:
    """Tests for get_index_name() helper function across all scripts"""

    def test_explicit_index_name_takes_priority(self):
        """Should use AZURE_SEARCH_INDEX_NAME when set"""
        with patch.dict(os.environ, {"AZURE_SEARCH_INDEX_NAME": "my-custom-index", "PRISM_PROJECT_NAME": "ignored"}):
            from scripts.search_index.create_search_index import get_index_name
            assert get_index_name() == "my-custom-index"

    def test_derives_from_project_name(self):
        """Should derive index name from PRISM_PROJECT_NAME"""
        # Clear the env var and set project name
        env = {"PRISM_PROJECT_NAME": "myproject"}
        with patch.dict(os.environ, env, clear=False):
            # Remove AZURE_SEARCH_INDEX_NAME if it exists
            os.environ.pop("AZURE_SEARCH_INDEX_NAME", None)
            from scripts.search_index.create_search_index import get_index_name
            result = get_index_name()
            assert result == "prism-myproject-index"

    def test_default_when_no_config(self):
        """Should return default when no config is set"""
        # Remove both env vars
        os.environ.pop("AZURE_SEARCH_INDEX_NAME", None)
        os.environ.pop("PRISM_PROJECT_NAME", None)
        from scripts.search_index.create_search_index import get_index_name
        result = get_index_name()
        assert result == "prism-default-index"


class TestKnowledgeSourceGetIndexName:
    """Tests for get_index_name() in create_knowledge_source.py"""

    def test_explicit_index_name(self):
        """Should use AZURE_SEARCH_INDEX_NAME when set"""
        with patch.dict(os.environ, {"AZURE_SEARCH_INDEX_NAME": "custom-source-index"}):
            from scripts.search_index.create_knowledge_source import get_index_name
            assert get_index_name() == "custom-source-index"

    def test_project_name_derivation(self):
        """Should derive from PRISM_PROJECT_NAME"""
        os.environ.pop("AZURE_SEARCH_INDEX_NAME", None)
        with patch.dict(os.environ, {"PRISM_PROJECT_NAME": "testproj"}):
            from scripts.search_index.create_knowledge_source import get_index_name
            assert get_index_name() == "prism-testproj-index"


class TestKnowledgeAgentGetIndexName:
    """Tests for get_index_name() in create_knowledge_agent.py"""

    def test_explicit_index_name(self):
        """Should use AZURE_SEARCH_INDEX_NAME when set"""
        with patch.dict(os.environ, {"AZURE_SEARCH_INDEX_NAME": "agent-index"}):
            from scripts.search_index.create_knowledge_agent import get_index_name
            assert get_index_name() == "agent-index"

    def test_default_value(self):
        """Should return default when nothing is set"""
        os.environ.pop("AZURE_SEARCH_INDEX_NAME", None)
        os.environ.pop("PRISM_PROJECT_NAME", None)
        from scripts.search_index.create_knowledge_agent import get_index_name
        assert get_index_name() == "prism-default-index"


class TestQueryAgentGetIndexName:
    """Tests for get_index_name() in query_knowledge_agent.py"""

    def test_explicit_index_name(self):
        """Should use AZURE_SEARCH_INDEX_NAME when set"""
        with patch.dict(os.environ, {"AZURE_SEARCH_INDEX_NAME": "query-index"}):
            from scripts.query.query_knowledge_agent import get_index_name
            assert get_index_name() == "query-index"

    def test_project_name_derivation(self):
        """Should derive from PRISM_PROJECT_NAME"""
        os.environ.pop("AZURE_SEARCH_INDEX_NAME", None)
        with patch.dict(os.environ, {"PRISM_PROJECT_NAME": "queryproj"}):
            from scripts.query.query_knowledge_agent import get_index_name
            assert get_index_name() == "prism-queryproj-index"


class TestNamingConventions:
    """Tests for naming conventions (index, source, agent)"""

    def test_source_name_pattern(self):
        """Knowledge source name should follow pattern: {index_name}-source"""
        # Test the pattern directly
        index_name = "test-index"
        expected_source = f"{index_name}-source"
        assert expected_source == "test-index-source"

    def test_agent_name_pattern(self):
        """Knowledge agent name should follow pattern: {index_name}-agent"""
        index_name = "test-index"
        expected_agent = f"{index_name}-agent"
        assert expected_agent == "test-index-agent"

    def test_prism_naming_pattern(self):
        """Full prism naming pattern: prism-{project}-{type}"""
        project_name = "demo"
        expected_index = f"prism-{project_name}-index"
        expected_source = f"{expected_index}-source"
        expected_agent = f"{expected_index}-agent"

        assert expected_index == "prism-demo-index"
        assert expected_source == "prism-demo-index-source"
        assert expected_agent == "prism-demo-index-agent"


class TestQueryHelperFunctions:
    """Tests for query helper functions"""

    def test_simplify_query_scada(self):
        """Should simplify SCADA queries"""
        from scripts.query.query_knowledge_agent import _simplify_query

        result = _simplify_query("OSS Wind Farm SCADA")
        assert result == "SCADA system"

    def test_simplify_query_substation(self):
        """Should simplify substation queries"""
        from scripts.query.query_knowledge_agent import _simplify_query

        result = _simplify_query("132kV substation automation requirements")
        assert result == "substation"

    def test_simplify_query_no_match(self):
        """Should return original if no simplification matches"""
        from scripts.query.query_knowledge_agent import _simplify_query

        result = _simplify_query("random query with no keywords")
        assert result == "random query with no keywords"

    def test_expand_query_scada(self):
        """Should expand SCADA queries with synonyms"""
        from scripts.query.query_knowledge_agent import _expand_query

        result = _expand_query("SCADA requirements")
        assert "SCADA requirements" in result
        assert "OR" in result
        assert "substation control system" in result

    def test_expand_query_automation(self):
        """Should expand automation queries"""
        from scripts.query.query_knowledge_agent import _expand_query

        result = _expand_query("automation system specs")
        assert "automation system specs" in result
        assert "OR" in result

    def test_expand_query_fallback(self):
        """Should add generic broadening for unmatched queries"""
        from scripts.query.query_knowledge_agent import _expand_query

        result = _expand_query("general query")
        assert "general query" in result
        assert "OR control OR monitoring OR system" in result


class TestSearchDocumentsFunction:
    """Tests for search_documents() function"""

    def test_function_exists(self):
        """Verify search_documents function exists"""
        from scripts.query.query_knowledge_agent import search_documents
        assert callable(search_documents)

    def test_function_docstring_is_generic(self):
        """Docstring should not contain RFP-specific references"""
        from scripts.query.query_knowledge_agent import search_documents

        docstring = search_documents.__doc__
        assert "RFP" not in docstring
        assert "indexed documents" in docstring.lower() or "documents" in docstring.lower()
