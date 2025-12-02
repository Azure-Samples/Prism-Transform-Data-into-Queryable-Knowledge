"""
Tests for pipeline service (Phase 5: Pipeline Endpoints)

These tests focus on the PipelineService class and its methods.
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add project root to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from apps.api.app.services.pipeline_service import (
    PipelineService,
    PipelineStage,
    TaskStatus,
    PipelineTask
)


class TestPipelineStageEnum:
    """Tests for PipelineStage enum"""

    def test_all_stages_exist(self):
        """All expected pipeline stages should exist"""
        expected_stages = [
            'process', 'deduplicate', 'chunk', 'embed',
            'index_create', 'index_upload', 'source_create', 'agent_create'
        ]
        for stage in expected_stages:
            assert PipelineStage(stage) is not None

    def test_stage_values(self):
        """Stage values should match their names"""
        assert PipelineStage.PROCESS.value == 'process'
        assert PipelineStage.CHUNK.value == 'chunk'
        assert PipelineStage.EMBED.value == 'embed'
        assert PipelineStage.INDEX_CREATE.value == 'index_create'
        assert PipelineStage.AGENT_CREATE.value == 'agent_create'


class TestTaskStatus:
    """Tests for TaskStatus enum"""

    def test_all_statuses_exist(self):
        """All expected task statuses should exist"""
        expected_statuses = ['pending', 'running', 'completed', 'failed']
        for status in expected_statuses:
            assert TaskStatus(status) is not None

    def test_status_values(self):
        """Status values should match their names"""
        assert TaskStatus.PENDING.value == 'pending'
        assert TaskStatus.RUNNING.value == 'running'
        assert TaskStatus.COMPLETED.value == 'completed'
        assert TaskStatus.FAILED.value == 'failed'


class TestPipelineTask:
    """Tests for PipelineTask dataclass"""

    def test_task_creation(self):
        """Should create a task with required fields"""
        task = PipelineTask(
            id="test-123",
            project_id="myproject",
            stage=PipelineStage.PROCESS
        )
        assert task.id == "test-123"
        assert task.project_id == "myproject"
        assert task.stage == PipelineStage.PROCESS
        assert task.status == TaskStatus.PENDING  # Default
        assert task.started_at is None
        assert task.completed_at is None
        assert task.error is None

    def test_task_with_status(self):
        """Should create a task with custom status"""
        task = PipelineTask(
            id="test-456",
            project_id="myproject",
            stage=PipelineStage.CHUNK,
            status=TaskStatus.RUNNING
        )
        assert task.status == TaskStatus.RUNNING


class TestPipelineService:
    """Tests for PipelineService class"""

    def test_service_initialization(self):
        """Should initialize with correct paths"""
        service = PipelineService()
        assert service.projects_dir is not None
        assert 'projects' in service.projects_dir

    def test_get_pipeline_stages(self):
        """Should return list of all pipeline stages"""
        service = PipelineService()
        stages = service.get_pipeline_stages()

        assert len(stages) == 8
        stage_ids = [s['id'] for s in stages]
        assert 'process' in stage_ids
        assert 'chunk' in stage_ids
        assert 'embed' in stage_ids
        assert 'index_create' in stage_ids
        assert 'agent_create' in stage_ids

    def test_get_pipeline_stages_have_descriptions(self):
        """Each stage should have name and description"""
        service = PipelineService()
        stages = service.get_pipeline_stages()

        for stage in stages:
            assert 'id' in stage
            assert 'name' in stage
            assert 'description' in stage
            assert len(stage['name']) > 0
            assert len(stage['description']) > 0

    def test_create_task(self):
        """Should create and store a task"""
        service = PipelineService()
        task = service._create_task("testproject", PipelineStage.PROCESS)

        assert task.id is not None
        assert task.project_id == "testproject"
        assert task.stage == PipelineStage.PROCESS
        assert task.status == TaskStatus.PENDING

        # Task should be stored
        retrieved = service.get_task(task.id)
        assert retrieved is not None
        assert retrieved.id == task.id

    def test_get_task_not_found(self):
        """Should return None for non-existent task"""
        service = PipelineService()
        result = service.get_task("nonexistent-task-id")
        assert result is None

    def test_list_tasks_empty(self):
        """Should return empty list when no tasks"""
        service = PipelineService()
        tasks = service.list_tasks("newproject")
        assert tasks == []

    def test_list_tasks_filtered_by_project(self):
        """Should filter tasks by project"""
        service = PipelineService()

        # Create tasks for different projects
        task1 = service._create_task("project1", PipelineStage.PROCESS)
        task2 = service._create_task("project2", PipelineStage.CHUNK)
        task3 = service._create_task("project1", PipelineStage.EMBED)

        # Filter by project1
        project1_tasks = service.list_tasks("project1")
        assert len(project1_tasks) == 2
        assert all(t.project_id == "project1" for t in project1_tasks)

        # Filter by project2
        project2_tasks = service.list_tasks("project2")
        assert len(project2_tasks) == 1
        assert project2_tasks[0].project_id == "project2"

    def test_update_task(self):
        """Should update task fields"""
        service = PipelineService()
        task = service._create_task("testproject", PipelineStage.PROCESS)

        # Update status
        service._update_task(task.id, status=TaskStatus.RUNNING)
        updated = service.get_task(task.id)
        assert updated.status == TaskStatus.RUNNING

        # Update with error
        service._update_task(task.id, status=TaskStatus.FAILED, error="Test error")
        updated = service.get_task(task.id)
        assert updated.status == TaskStatus.FAILED
        assert updated.error == "Test error"


class TestPipelineStageDescriptions:
    """Tests for pipeline stage descriptions"""

    def test_process_stage_description(self):
        """Process stage should have correct description"""
        service = PipelineService()
        stages = service.get_pipeline_stages()
        process_stage = next(s for s in stages if s['id'] == 'process')

        assert 'extract' in process_stage['description'].lower() or 'process' in process_stage['description'].lower()

    def test_chunk_stage_description(self):
        """Chunk stage should mention RAG or semantic"""
        service = PipelineService()
        stages = service.get_pipeline_stages()
        chunk_stage = next(s for s in stages if s['id'] == 'chunk')

        desc_lower = chunk_stage['description'].lower()
        assert 'chunk' in desc_lower or 'split' in desc_lower

    def test_embed_stage_description(self):
        """Embed stage should mention embeddings or vectors"""
        service = PipelineService()
        stages = service.get_pipeline_stages()
        embed_stage = next(s for s in stages if s['id'] == 'embed')

        desc_lower = embed_stage['description'].lower()
        assert 'embed' in desc_lower or 'vector' in desc_lower

    def test_agent_stage_description(self):
        """Agent stage should mention agent or retrieval"""
        service = PipelineService()
        stages = service.get_pipeline_stages()
        agent_stage = next(s for s in stages if s['id'] == 'agent_create')

        desc_lower = agent_stage['description'].lower()
        assert 'agent' in desc_lower or 'retrieval' in desc_lower
