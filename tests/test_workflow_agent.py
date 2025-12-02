"""
Tests for workflow_agent module (workflows/workflow_agent.py)

Note: These tests focus on config loading and helper functions.
Agent creation tests are skipped as they require Azure OpenAI credentials.
"""
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Add project root to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestLoadWorkflowConfig:
    """Tests for load_workflow_config()"""

    def test_load_config_success(self, sample_project, monkeypatch):
        """Should load workflow config from project folder"""
        base_path, project_name = sample_project

        # Change to temp directory so relative paths work
        monkeypatch.chdir(base_path)

        from workflows.workflow_agent import load_workflow_config
        config = load_workflow_config(project_name)

        assert config is not None
        assert "sections" in config
        assert len(config["sections"]) == 2
        assert config["sections"][0]["id"] == "section1"

    def test_load_config_not_found(self, temp_projects_dir, monkeypatch):
        """Should raise FileNotFoundError if config doesn't exist"""
        monkeypatch.chdir(temp_projects_dir)

        from workflows.workflow_agent import load_workflow_config

        with pytest.raises(FileNotFoundError):
            load_workflow_config("nonexistent")


class TestListProjectSections:
    """Tests for list_project_sections()"""

    def test_list_sections_success(self, sample_project, monkeypatch):
        """Should return list of section info dicts"""
        base_path, project_name = sample_project
        monkeypatch.chdir(base_path)

        # Mock the Azure OpenAI client since we don't have credentials
        with patch('workflows.workflow_agent.AzureOpenAIChatClient'):
            from workflows.workflow_agent import list_project_sections
            sections = list_project_sections(project_name)

        assert len(sections) == 2
        assert sections[0]["id"] == "section1"
        assert sections[0]["name"] == "Test Section 1"
        assert sections[0]["question_count"] == 2


class TestWorkflowAgentFactory:
    """Tests for WorkflowAgentFactory class"""

    def test_factory_init_loads_config(self, sample_project, monkeypatch):
        """Should load config on initialization"""
        base_path, project_name = sample_project
        monkeypatch.chdir(base_path)

        with patch('workflows.workflow_agent.AzureOpenAIChatClient'):
            from workflows.workflow_agent import WorkflowAgentFactory
            factory = WorkflowAgentFactory(project_name)

        assert factory.project_name == project_name
        assert factory.config is not None
        assert len(factory.config["sections"]) == 2

    def test_factory_get_all_section_ids(self, sample_project, monkeypatch):
        """Should return all section IDs"""
        base_path, project_name = sample_project
        monkeypatch.chdir(base_path)

        with patch('workflows.workflow_agent.AzureOpenAIChatClient'):
            from workflows.workflow_agent import WorkflowAgentFactory
            factory = WorkflowAgentFactory(project_name)
            section_ids = factory.get_all_section_ids()

        assert section_ids == ["section1", "section2"]

    def test_factory_get_section_info_exists(self, sample_project, monkeypatch):
        """Should return info for existing section"""
        base_path, project_name = sample_project
        monkeypatch.chdir(base_path)

        with patch('workflows.workflow_agent.AzureOpenAIChatClient'):
            from workflows.workflow_agent import WorkflowAgentFactory
            factory = WorkflowAgentFactory(project_name)
            info = factory.get_section_info("section1")

        assert info is not None
        assert info["id"] == "section1"
        assert info["name"] == "Test Section 1"
        assert info["question_count"] == 2

    def test_factory_get_section_info_not_exists(self, sample_project, monkeypatch):
        """Should return None for non-existent section"""
        base_path, project_name = sample_project
        monkeypatch.chdir(base_path)

        with patch('workflows.workflow_agent.AzureOpenAIChatClient'):
            from workflows.workflow_agent import WorkflowAgentFactory
            factory = WorkflowAgentFactory(project_name)
            info = factory.get_section_info("nonexistent")

        assert info is None

    def test_factory_build_agent_instructions(self, sample_project, monkeypatch):
        """Should build correct agent instructions from template and question"""
        base_path, project_name = sample_project
        monkeypatch.chdir(base_path)

        with patch('workflows.workflow_agent.AzureOpenAIChatClient'):
            from workflows.workflow_agent import WorkflowAgentFactory
            factory = WorkflowAgentFactory(project_name)

            section = factory.config["sections"][0]
            question = section["questions"][0]
            instructions = factory._build_agent_instructions(section, question)

        # Check that template, question, and instructions are included
        assert "Answer the following question based on the documents" in instructions
        assert "What is the main topic?" in instructions
        assert "Look for introductory content" in instructions
        assert "Response Format" in instructions


class TestWorkflowAgentFactoryOutputDir:
    """Tests for output directory creation"""

    def test_factory_creates_output_dir(self, sample_project, monkeypatch):
        """Should create output directory on initialization"""
        base_path, project_name = sample_project
        monkeypatch.chdir(base_path)

        # Remove output dir first
        output_dir = Path(base_path) / "projects" / project_name / "output"
        if output_dir.exists():
            import shutil
            shutil.rmtree(output_dir)

        with patch('workflows.workflow_agent.AzureOpenAIChatClient'):
            from workflows.workflow_agent import WorkflowAgentFactory
            factory = WorkflowAgentFactory(project_name)

        assert factory.output_dir.exists()


class TestWorkflowConfigValidation:
    """Tests for handling invalid workflow configs"""

    def test_empty_sections(self, temp_projects_dir, monkeypatch):
        """Should handle empty sections list"""
        projects_dir = temp_projects_dir / "projects"
        projects_dir.mkdir()
        project_path = projects_dir / "empty_sections"
        project_path.mkdir()
        (project_path / "output").mkdir()

        # Create config with empty sections
        with open(project_path / "workflow_config.json", 'w') as f:
            json.dump({"sections": []}, f)

        monkeypatch.chdir(temp_projects_dir)

        with patch('workflows.workflow_agent.AzureOpenAIChatClient'):
            from workflows.workflow_agent import WorkflowAgentFactory
            factory = WorkflowAgentFactory("empty_sections")

        assert factory.get_all_section_ids() == []

    def test_section_without_questions(self, temp_projects_dir, monkeypatch):
        """Should handle section with no questions"""
        projects_dir = temp_projects_dir / "projects"
        projects_dir.mkdir()
        project_path = projects_dir / "no_questions"
        project_path.mkdir()
        (project_path / "output").mkdir()

        # Create config with section but no questions
        config = {
            "sections": [
                {
                    "id": "empty_section",
                    "name": "Empty Section",
                    "template": "Test template"
                }
            ]
        }
        with open(project_path / "workflow_config.json", 'w') as f:
            json.dump(config, f)

        monkeypatch.chdir(temp_projects_dir)

        with patch('workflows.workflow_agent.AzureOpenAIChatClient'):
            from workflows.workflow_agent import WorkflowAgentFactory
            factory = WorkflowAgentFactory("no_questions")
            info = factory.get_section_info("empty_section")

        assert info["question_count"] == 0
