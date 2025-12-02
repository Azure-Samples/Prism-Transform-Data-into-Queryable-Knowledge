"""
Tests for ProjectService (apps/api/app/services/project_service.py)
"""
import os
import json
from pathlib import Path
import pytest

# Add project root to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from apps.api.app.services.project_service import ProjectService


class TestProjectServiceListProjects:
    """Tests for ProjectService.list_projects()"""

    def test_list_projects_empty(self, empty_projects_dir):
        """Should return empty list when no projects exist"""
        service = ProjectService(base_path=empty_projects_dir)
        projects = service.list_projects()
        assert projects == []

    def test_list_projects_with_project(self, sample_project):
        """Should return list with project info"""
        base_path, project_name = sample_project
        service = ProjectService(base_path=base_path)
        projects = service.list_projects()

        assert len(projects) == 1
        assert projects[0].name == project_name

    def test_list_projects_ignores_hidden(self, temp_projects_dir):
        """Should ignore hidden directories (starting with .)"""
        projects_dir = temp_projects_dir / "projects"
        projects_dir.mkdir()

        # Create hidden directory
        hidden_dir = projects_dir / ".hidden"
        hidden_dir.mkdir()

        # Create regular project
        regular_dir = projects_dir / "regular"
        regular_dir.mkdir()
        (regular_dir / "documents").mkdir()
        (regular_dir / "output").mkdir()

        service = ProjectService(base_path=str(temp_projects_dir))
        projects = service.list_projects()

        assert len(projects) == 1
        assert projects[0].name == "regular"


class TestProjectServiceGetProjectInfo:
    """Tests for ProjectService.get_project_info()"""

    def test_get_project_info_exists(self, sample_project):
        """Should return project info for existing project"""
        base_path, project_name = sample_project
        service = ProjectService(base_path=base_path)
        info = service.get_project_info(project_name)

        assert info is not None
        assert info.name == project_name
        assert info.document_count == 0
        assert info.has_extraction_results is False

    def test_get_project_info_not_exists(self, empty_projects_dir):
        """Should return None for non-existent project"""
        service = ProjectService(base_path=empty_projects_dir)
        info = service.get_project_info("nonexistent")
        assert info is None

    def test_get_project_info_with_documents(self, project_with_documents):
        """Should count documents correctly"""
        base_path, project_name = project_with_documents
        service = ProjectService(base_path=base_path)
        info = service.get_project_info(project_name)

        assert info is not None
        assert info.document_count == 3  # 2 in root + 1 in subdir


class TestProjectServiceCreateProject:
    """Tests for ProjectService.create_project()"""

    def test_create_project_success(self, temp_projects_dir):
        """Should create project with correct structure"""
        projects_dir = temp_projects_dir / "projects"
        projects_dir.mkdir()

        service = ProjectService(base_path=str(temp_projects_dir))
        result = service.create_project("new_project")

        assert result is True

        # Check directory structure
        project_path = projects_dir / "new_project"
        assert project_path.exists()
        assert (project_path / "documents").exists()
        assert (project_path / "output").exists()
        assert (project_path / "config.json").exists()
        assert (project_path / "workflow_config.json").exists()

    def test_create_project_config_content(self, temp_projects_dir):
        """Should create config.json with correct content"""
        projects_dir = temp_projects_dir / "projects"
        projects_dir.mkdir()

        service = ProjectService(base_path=str(temp_projects_dir))
        service.create_project("new_project")

        config_path = projects_dir / "new_project" / "config.json"
        with open(config_path) as f:
            config = json.load(f)

        assert config["name"] == "new_project"
        assert "created_at" in config
        assert config["status"]["has_documents"] is False
        assert config["status"]["is_processed"] is False

    def test_create_project_workflow_config(self, temp_projects_dir):
        """Should create workflow_config.json with empty sections"""
        projects_dir = temp_projects_dir / "projects"
        projects_dir.mkdir()

        service = ProjectService(base_path=str(temp_projects_dir))
        service.create_project("new_project")

        workflow_path = projects_dir / "new_project" / "workflow_config.json"
        with open(workflow_path) as f:
            workflow = json.load(f)

        assert "sections" in workflow
        assert workflow["sections"] == []

    def test_create_project_already_exists(self, sample_project):
        """Should return False if project already exists"""
        base_path, project_name = sample_project
        service = ProjectService(base_path=base_path)
        result = service.create_project(project_name)
        assert result is False


class TestProjectServiceDeleteProject:
    """Tests for ProjectService.delete_project()"""

    def test_delete_project_success(self, sample_project):
        """Should delete project and all contents"""
        base_path, project_name = sample_project
        service = ProjectService(base_path=base_path)

        result = service.delete_project(project_name)
        assert result is True

        # Verify deleted
        project_path = Path(base_path) / "projects" / project_name
        assert not project_path.exists()

    def test_delete_project_not_exists(self, empty_projects_dir):
        """Should return False if project doesn't exist"""
        service = ProjectService(base_path=empty_projects_dir)
        result = service.delete_project("nonexistent")
        assert result is False


class TestProjectServiceProjectExists:
    """Tests for ProjectService.project_exists()"""

    def test_project_exists_true(self, sample_project):
        """Should return True for existing project"""
        base_path, project_name = sample_project
        service = ProjectService(base_path=base_path)
        assert service.project_exists(project_name) is True

    def test_project_exists_false(self, empty_projects_dir):
        """Should return False for non-existent project"""
        service = ProjectService(base_path=empty_projects_dir)
        assert service.project_exists("nonexistent") is False


class TestProjectServicePaths:
    """Tests for path helper methods"""

    def test_get_documents_path(self, sample_project):
        """Should return correct documents path"""
        base_path, project_name = sample_project
        service = ProjectService(base_path=base_path)
        path = service.get_documents_path(project_name)
        # Platform-agnostic check
        assert "projects" in path and project_name in path and "documents" in path

    def test_get_output_path(self, sample_project):
        """Should return correct output path"""
        base_path, project_name = sample_project
        service = ProjectService(base_path=base_path)
        path = service.get_output_path(project_name)
        # Platform-agnostic check
        assert "projects" in path and project_name in path and "output" in path

    def test_get_results_csv_path(self, sample_project):
        """Should return correct results.csv path"""
        base_path, project_name = sample_project
        service = ProjectService(base_path=base_path)
        path = service.get_results_csv_path(project_name)
        # Platform-agnostic check
        assert "projects" in path and project_name in path and "results.csv" in path
