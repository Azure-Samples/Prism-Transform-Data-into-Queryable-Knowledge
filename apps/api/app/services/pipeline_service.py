"""
Pipeline Service - Manages document processing pipeline operations

Now uses StorageService for persistence (Azure Blob Storage or local fallback).
When blob storage is enabled, files are synced to local before processing
and synced back to blob after processing completes.

Provides async task execution for:
- Document extraction (process)
- Deduplication
- Chunking
- Embedding
- Index creation and upload
- Knowledge source/agent creation
"""

import os
import sys
import asyncio
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
import threading
import traceback

from apps.api.app.services.storage_service import get_storage_service


class PipelineStage(str, Enum):
    """Pipeline stages"""
    PROCESS = "process"
    DEDUPLICATE = "deduplicate"
    CHUNK = "chunk"
    EMBED = "embed"
    INDEX_CREATE = "index_create"
    INDEX_UPLOAD = "index_upload"
    SOURCE_CREATE = "source_create"
    AGENT_CREATE = "agent_create"


class TaskStatus(str, Enum):
    """Task status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PipelineProgress:
    """Progress information for a pipeline task"""
    current: int = 0
    total: int = 0
    message: str = ""
    percent: float = 0.0


@dataclass
class PipelineTask:
    """Represents a pipeline task"""
    id: str
    project_id: str
    stage: PipelineStage
    status: TaskStatus = TaskStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    output: List[str] = field(default_factory=list)
    progress: PipelineProgress = field(default_factory=PipelineProgress)


class PipelineService:
    """Service for managing pipeline operations with blob storage support"""

    # Class-level storage for progress callbacks (allows scripts to report progress)
    _progress_callbacks: Dict[str, 'PipelineService'] = {}

    def __init__(self):
        """Initialize pipeline service with storage backend"""
        self.storage = get_storage_service()

        # Task storage (in production, use Redis or database)
        self._tasks: Dict[str, PipelineTask] = {}
        self._lock = threading.Lock()

    def update_progress(self, task_id: str, current: int, total: int, message: str = "") -> None:
        """Update progress for a task"""
        with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                task.progress.current = current
                task.progress.total = total
                task.progress.message = message
                task.progress.percent = (current / total * 100) if total > 0 else 0

    def get_task(self, task_id: str) -> Optional[PipelineTask]:
        """Get task by ID"""
        with self._lock:
            return self._tasks.get(task_id)

    def list_tasks(self, project_id: Optional[str] = None) -> List[PipelineTask]:
        """List all tasks, optionally filtered by project"""
        with self._lock:
            tasks = list(self._tasks.values())
            if project_id:
                tasks = [t for t in tasks if t.project_id == project_id]
            return sorted(tasks, key=lambda t: t.started_at or datetime.min, reverse=True)

    def _create_task(self, project_id: str, stage: PipelineStage) -> PipelineTask:
        """Create a new task"""
        task = PipelineTask(
            id=str(uuid.uuid4()),
            project_id=project_id,
            stage=stage,
            status=TaskStatus.PENDING
        )
        with self._lock:
            self._tasks[task.id] = task
        return task

    def _update_task(self, task_id: str, **kwargs) -> None:
        """Update task fields"""
        with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                for key, value in kwargs.items():
                    setattr(task, key, value)

    async def run_pipeline_stage(
        self,
        project_id: str,
        stage: PipelineStage,
        options: dict = None
    ) -> PipelineTask:
        """
        Run a pipeline stage asynchronously.

        Args:
            project_id: Project name
            stage: Pipeline stage to run
            options: Optional dict with stage-specific options (e.g., {"force": True})

        Returns:
            PipelineTask with status
        """
        # Create task
        task = self._create_task(project_id, stage)
        options = options or {}

        # Run in background thread to not block
        def run_stage():
            self._execute_stage(task.id, project_id, stage, options)

        thread = threading.Thread(target=run_stage)
        thread.start()

        # Return task immediately
        return task

    def _execute_stage(self, task_id: str, project_id: str, stage: PipelineStage, options: dict = None) -> None:
        """Execute a pipeline stage (runs in background thread)"""
        from apps.api.app.services.progress_tracker import set_progress_callback, clear_progress_callback
        options = options or {}

        self._update_task(
            task_id,
            status=TaskStatus.RUNNING,
            started_at=datetime.utcnow()
        )

        # Set up progress callback so scripts can report progress
        def progress_callback(current: int, total: int, message: str = ""):
            self.update_progress(task_id, current, total, message)

        set_progress_callback(task_id, progress_callback)

        try:
            # Set environment for the scripts
            os.environ['PRISM_PROJECT_NAME'] = project_id

            # Import and run the appropriate module
            if stage == PipelineStage.PROCESS:
                from scripts.testing import process_all_documents
                process_all_documents.main(force_reextract=options.get("force", False))

            elif stage == PipelineStage.DEDUPLICATE:
                from scripts.rag import deduplicate_documents
                deduplicate_documents.main()

            elif stage == PipelineStage.CHUNK:
                from scripts.rag import chunk_documents
                chunk_documents.main()

            elif stage == PipelineStage.EMBED:
                from scripts.rag import generate_embeddings
                generate_embeddings.main()

            elif stage == PipelineStage.INDEX_CREATE:
                from scripts.search_index import create_search_index
                create_search_index.main()

            elif stage == PipelineStage.INDEX_UPLOAD:
                from scripts.search_index import upload_to_search
                upload_to_search.main()

            elif stage == PipelineStage.SOURCE_CREATE:
                from scripts.search_index import create_knowledge_source
                create_knowledge_source.main()

            elif stage == PipelineStage.AGENT_CREATE:
                from scripts.search_index import create_knowledge_agent
                create_knowledge_agent.main()

            self._update_task(
                task_id,
                status=TaskStatus.COMPLETED,
                completed_at=datetime.utcnow()
            )

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            self._update_task(
                task_id,
                status=TaskStatus.FAILED,
                completed_at=datetime.utcnow(),
                error=error_msg
            )
        finally:
            # Always clear the progress callback
            clear_progress_callback()

    def get_pipeline_stages(self) -> List[Dict[str, Any]]:
        """Get list of all pipeline stages with descriptions"""
        return [
            {
                "id": PipelineStage.PROCESS.value,
                "name": "Extract Documents",
                "description": "Process documents and extract content to markdown"
            },
            {
                "id": PipelineStage.DEDUPLICATE.value,
                "name": "Deduplicate",
                "description": "Analyze and remove duplicate content"
            },
            {
                "id": PipelineStage.CHUNK.value,
                "name": "Chunk Documents",
                "description": "Split documents into semantic chunks for RAG"
            },
            {
                "id": PipelineStage.EMBED.value,
                "name": "Generate Embeddings",
                "description": "Create vector embeddings for chunks"
            },
            {
                "id": PipelineStage.INDEX_CREATE.value,
                "name": "Create Index",
                "description": "Create Azure AI Search index"
            },
            {
                "id": PipelineStage.INDEX_UPLOAD.value,
                "name": "Upload to Index",
                "description": "Upload embedded documents to search index"
            },
            {
                "id": PipelineStage.SOURCE_CREATE.value,
                "name": "Create Knowledge Source",
                "description": "Create knowledge source wrapper for index"
            },
            {
                "id": PipelineStage.AGENT_CREATE.value,
                "name": "Create Knowledge Agent",
                "description": "Create knowledge agent for agentic retrieval"
            }
        ]
