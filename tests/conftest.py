"""
Pytest configuration and fixtures for Prism tests.
"""
import os
import json
import shutil
import tempfile
from pathlib import Path
import pytest


@pytest.fixture
def temp_projects_dir(tmp_path):
    """
    Create a temporary base directory for testing.
    Returns the path to the temp directory (does NOT create projects subdir).
    """
    return tmp_path


@pytest.fixture
def sample_project(temp_projects_dir):
    """
    Create a sample project with config and workflow_config files.
    Returns (base_path, project_name).
    """
    project_name = "test_project"
    projects_dir = temp_projects_dir / "projects"
    project_path = projects_dir / project_name

    # Create project structure
    project_path.mkdir(parents=True)
    (project_path / "documents").mkdir()
    (project_path / "output").mkdir()

    # Create config.json
    config = {
        "name": project_name,
        "description": "Test project",
        "created_at": "2024-01-01T00:00:00Z",
        "status": {
            "has_documents": False,
            "is_processed": False,
            "is_indexed": False,
            "has_agent": False
        }
    }
    with open(project_path / "config.json", 'w') as f:
        json.dump(config, f, indent=2)

    # Create workflow_config.json
    workflow_config = {
        "sections": [
            {
                "id": "section1",
                "name": "Test Section 1",
                "template": "Answer the following question based on the documents.",
                "questions": [
                    {
                        "id": "q1",
                        "question": "What is the main topic?",
                        "instructions": "Look for introductory content"
                    },
                    {
                        "id": "q2",
                        "question": "What are the requirements?",
                        "instructions": "Search for requirement sections"
                    }
                ]
            },
            {
                "id": "section2",
                "name": "Test Section 2",
                "template": "Focus on technical details.",
                "questions": [
                    {
                        "id": "q1",
                        "question": "What is the system architecture?",
                        "instructions": "Look for architecture diagrams"
                    }
                ]
            }
        ]
    }
    with open(project_path / "workflow_config.json", 'w') as f:
        json.dump(workflow_config, f, indent=2)

    return str(temp_projects_dir), project_name


@pytest.fixture
def sample_project_with_results(sample_project):
    """
    Create a sample project with existing results.
    Returns (base_path, project_name).
    """
    base_path, project_name = sample_project
    project_path = Path(base_path) / "projects" / project_name

    # Create results.json
    results = {
        "sections": {
            "section1": {
                "name": "Test Section 1",
                "questions": {
                    "q1": {
                        "question": "What is the main topic?",
                        "answer": "Testing",
                        "reference": "test.pdf page 1",
                        "comments": "Found in introduction"
                    }
                }
            }
        }
    }
    results_path = project_path / "output" / "results.json"
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)

    return base_path, project_name


@pytest.fixture
def empty_projects_dir(temp_projects_dir):
    """
    Create an empty projects directory.
    Returns base_path.
    """
    return str(temp_projects_dir)


@pytest.fixture
def project_with_documents(sample_project):
    """
    Create a project with some sample document files.
    Returns (base_path, project_name).
    """
    base_path, project_name = sample_project
    project_path = Path(base_path) / "projects" / project_name / "documents"

    # Create sample files
    (project_path / "sample1.txt").write_text("Sample document 1 content")
    (project_path / "sample2.txt").write_text("Sample document 2 content")
    (project_path / "subdir").mkdir()
    (project_path / "subdir" / "sample3.txt").write_text("Nested document content")

    return base_path, project_name
