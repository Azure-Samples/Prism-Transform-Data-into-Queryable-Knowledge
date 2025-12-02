"""
Tests for WorkflowService (apps/api/app/services/workflow_service.py)
"""
import os
import json
from pathlib import Path
import pytest

# Add project root to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from apps.api.app.services.workflow_service import WorkflowService


class TestWorkflowServiceListSections:
    """Tests for WorkflowService.list_sections()"""

    def test_list_sections_with_config(self, sample_project):
        """Should return sections from workflow_config.json"""
        base_path, project_name = sample_project
        service = WorkflowService(base_path=base_path)
        sections = service.list_sections(project_name)

        assert len(sections) == 2
        assert sections[0].section_id == "section1"
        assert sections[0].section_name == "Test Section 1"
        assert sections[0].question_count == 2
        assert sections[1].section_id == "section2"
        assert sections[1].question_count == 1

    def test_list_sections_empty_config(self, temp_projects_dir):
        """Should return empty list if no sections configured"""
        projects_dir = temp_projects_dir / "projects"
        projects_dir.mkdir()
        project_path = projects_dir / "empty_project"
        project_path.mkdir()

        # Create empty workflow config
        with open(project_path / "workflow_config.json", 'w') as f:
            json.dump({"sections": []}, f)

        service = WorkflowService(base_path=str(temp_projects_dir))
        sections = service.list_sections("empty_project")

        assert sections == []

    def test_list_sections_no_config(self, temp_projects_dir):
        """Should return empty list if no config file"""
        projects_dir = temp_projects_dir / "projects"
        projects_dir.mkdir()
        (projects_dir / "no_config_project").mkdir()

        service = WorkflowService(base_path=str(temp_projects_dir))
        sections = service.list_sections("no_config_project")

        assert sections == []

    def test_list_sections_with_completion(self, sample_project_with_results):
        """Should calculate completion percentage correctly"""
        base_path, project_name = sample_project_with_results
        service = WorkflowService(base_path=base_path)
        sections = service.list_sections(project_name)

        # Section 1 has 2 questions, 1 answered
        section1 = sections[0]
        assert section1.completed_count == 1
        assert section1.completion_percentage == 50.0


class TestWorkflowServiceGetSection:
    """Tests for WorkflowService.get_section()"""

    def test_get_section_exists(self, sample_project):
        """Should return section dict for existing section"""
        base_path, project_name = sample_project
        service = WorkflowService(base_path=base_path)
        section = service.get_section(project_name, "section1")

        assert section is not None
        assert section["id"] == "section1"
        assert section["name"] == "Test Section 1"
        assert len(section["questions"]) == 2

    def test_get_section_not_exists(self, sample_project):
        """Should return None for non-existent section"""
        base_path, project_name = sample_project
        service = WorkflowService(base_path=base_path)
        section = service.get_section(project_name, "nonexistent")

        assert section is None


class TestWorkflowServiceCreateSection:
    """Tests for WorkflowService.create_section()"""

    def test_create_section_success(self, sample_project):
        """Should create new section in config"""
        base_path, project_name = sample_project
        service = WorkflowService(base_path=base_path)

        section_data = {
            "name": "New Section",
            "template": "Answer based on documents"
        }
        result = service.create_section(project_name, section_data)

        assert result is not None
        assert "id" in result
        assert result["name"] == "New Section"
        assert result["questions"] == []

        # Verify persisted
        sections = service.list_sections(project_name)
        assert len(sections) == 3

    def test_create_section_with_id(self, sample_project):
        """Should use provided ID if given"""
        base_path, project_name = sample_project
        service = WorkflowService(base_path=base_path)

        section_data = {
            "id": "custom_id",
            "name": "Custom Section",
            "template": "Test template"
        }
        result = service.create_section(project_name, section_data)

        assert result["id"] == "custom_id"


class TestWorkflowServiceUpdateSection:
    """Tests for WorkflowService.update_section()"""

    def test_update_section_success(self, sample_project):
        """Should update section properties"""
        base_path, project_name = sample_project
        service = WorkflowService(base_path=base_path)

        updated_data = {
            "name": "Updated Name",
            "template": "Updated template"
        }
        result = service.update_section(project_name, "section1", updated_data)

        assert result is not None
        assert result["name"] == "Updated Name"
        assert result["template"] == "Updated template"
        # Questions should be preserved
        assert len(result["questions"]) == 2

    def test_update_section_not_exists(self, sample_project):
        """Should return None for non-existent section"""
        base_path, project_name = sample_project
        service = WorkflowService(base_path=base_path)

        result = service.update_section(project_name, "nonexistent", {"name": "Test"})
        assert result is None


class TestWorkflowServiceDeleteSection:
    """Tests for WorkflowService.delete_section()"""

    def test_delete_section_success(self, sample_project):
        """Should delete section from config"""
        base_path, project_name = sample_project
        service = WorkflowService(base_path=base_path)

        result = service.delete_section(project_name, "section1")
        assert result is True

        # Verify deleted
        sections = service.list_sections(project_name)
        assert len(sections) == 1
        assert sections[0].section_id == "section2"

    def test_delete_section_not_exists(self, sample_project):
        """Should return False for non-existent section"""
        base_path, project_name = sample_project
        service = WorkflowService(base_path=base_path)

        result = service.delete_section(project_name, "nonexistent")
        assert result is False


class TestWorkflowServiceQuestions:
    """Tests for question CRUD operations"""

    def test_get_section_questions(self, sample_project):
        """Should return questions for section"""
        base_path, project_name = sample_project
        service = WorkflowService(base_path=base_path)

        questions = service.get_section_questions(project_name, "section1")
        assert len(questions) == 2
        assert questions[0]["id"] == "q1"
        assert questions[0]["question"] == "What is the main topic?"

    def test_add_question_success(self, sample_project):
        """Should add question to section"""
        base_path, project_name = sample_project
        service = WorkflowService(base_path=base_path)

        question_data = {
            "question": "New question?",
            "instructions": "New instructions"
        }
        result = service.add_question(project_name, "section1", question_data)

        assert result is not None
        assert "id" in result
        assert result["question"] == "New question?"

        # Verify persisted
        questions = service.get_section_questions(project_name, "section1")
        assert len(questions) == 3

    def test_update_question_success(self, sample_project):
        """Should update existing question"""
        base_path, project_name = sample_project
        service = WorkflowService(base_path=base_path)

        updated_data = {
            "question": "Updated question?",
            "instructions": "Updated instructions"
        }
        result = service.update_question(project_name, "section1", "q1", updated_data)

        assert result is not None
        assert result["question"] == "Updated question?"

    def test_delete_question_success(self, sample_project):
        """Should delete question from section"""
        base_path, project_name = sample_project
        service = WorkflowService(base_path=base_path)

        result = service.delete_question(project_name, "section1", "q1")
        assert result is True

        # Verify deleted
        questions = service.get_section_questions(project_name, "section1")
        assert len(questions) == 1
        assert questions[0]["id"] == "q2"


class TestWorkflowServiceResults:
    """Tests for results-related methods"""

    def test_get_project_results_exists(self, sample_project_with_results):
        """Should return results for project"""
        base_path, project_name = sample_project_with_results
        service = WorkflowService(base_path=base_path)

        results = service.get_project_results(project_name)
        assert results is not None
        assert results.project_id == project_name
        assert results.total_questions == 3  # 2 in section1 + 1 in section2
        assert results.answered_questions == 1

    def test_get_project_results_no_results(self, sample_project):
        """Should return None if no results file"""
        base_path, project_name = sample_project
        service = WorkflowService(base_path=base_path)

        results = service.get_project_results(project_name)
        assert results is None

    def test_clear_section_answers(self, sample_project_with_results):
        """Should clear answers for a section"""
        base_path, project_name = sample_project_with_results
        service = WorkflowService(base_path=base_path)

        cleared = service.clear_section_answers(project_name, "section1")
        assert cleared == 1  # 1 question was answered

        # Verify cleared
        results = service._get_results(project_name)
        assert results["sections"]["section1"]["questions"] == {}
