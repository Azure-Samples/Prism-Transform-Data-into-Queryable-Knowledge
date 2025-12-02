"""
Pipeline API - Manage document processing pipeline operations
"""
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from apps.api.app.services.pipeline_service import (
    PipelineService,
    PipelineStage,
    TaskStatus
)
from apps.api.app.services.project_service import ProjectService


router = APIRouter()
pipeline_service = PipelineService()
project_service = ProjectService()


# ==================== Response Models ====================

class PipelineStageInfo(BaseModel):
    id: str
    name: str
    description: str


class TaskResponse(BaseModel):
    id: str
    project_id: str
    stage: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


class RunStageRequest(BaseModel):
    stage: str
    force: bool = False  # Force re-processing of already-completed items


# ==================== Endpoints ====================

@router.get("/stages", response_model=List[PipelineStageInfo])
async def list_pipeline_stages():
    """List all available pipeline stages"""
    return pipeline_service.get_pipeline_stages()


@router.post("/{project_id}/run")
async def run_pipeline_stage(project_id: str, request: RunStageRequest):
    """
    Run a pipeline stage for a project.

    Available stages:
    - process: Extract documents to markdown
    - deduplicate: Remove duplicate content
    - chunk: Chunk documents for RAG
    - embed: Generate embeddings
    - index_create: Create Azure AI Search index
    - index_upload: Upload to index
    - source_create: Create knowledge source
    - agent_create: Create knowledge agent
    """
    try:
        # Validate project exists
        if not project_service.project_exists(project_id):
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

        # Validate stage
        try:
            stage = PipelineStage(request.stage)
        except ValueError:
            valid_stages = [s.value for s in PipelineStage]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid stage '{request.stage}'. Valid stages: {valid_stages}"
            )

        # Start the pipeline stage
        options = {"force": request.force}
        task = await pipeline_service.run_pipeline_stage(project_id, stage, options=options)

        return {
            "task_id": task.id,
            "project_id": task.project_id,
            "stage": task.stage.value,
            "status": task.status.value,
            "force": request.force,
            "message": f"Pipeline stage '{stage.value}' started for project '{project_id}'"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/tasks")
async def list_project_tasks(project_id: str):
    """List all pipeline tasks for a project"""
    try:
        if not project_service.project_exists(project_id):
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

        tasks = pipeline_service.list_tasks(project_id)
        return {
            "tasks": [
                {
                    "id": t.id,
                    "stage": t.stage.value,
                    "status": t.status.value,
                    "started_at": t.started_at.isoformat() if t.started_at else None,
                    "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                    "error": t.error
                }
                for t in tasks
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get status of a specific pipeline task"""
    try:
        task = pipeline_service.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

        return {
            "id": task.id,
            "project_id": task.project_id,
            "stage": task.stage.value,
            "status": task.status.value,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "error": task.error,
            "progress": {
                "current": task.progress.current,
                "total": task.progress.total,
                "percent": task.progress.percent,
                "message": task.progress.message
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/run-all")
async def run_full_pipeline(project_id: str):
    """
    Run the full pipeline for a project (all stages in sequence).

    Note: This starts the first stage immediately. Subsequent stages
    should be triggered after each stage completes (via polling or webhooks).
    """
    try:
        if not project_service.project_exists(project_id):
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

        # Start with process stage
        task = await pipeline_service.run_pipeline_stage(project_id, PipelineStage.PROCESS)

        return {
            "task_id": task.id,
            "project_id": project_id,
            "stage": task.stage.value,
            "status": task.status.value,
            "message": f"Full pipeline started. First stage: {task.stage.value}",
            "next_stages": [
                PipelineStage.DEDUPLICATE.value,
                PipelineStage.CHUNK.value,
                PipelineStage.EMBED.value,
                PipelineStage.INDEX_CREATE.value,
                PipelineStage.INDEX_UPLOAD.value,
                PipelineStage.SOURCE_CREATE.value,
                PipelineStage.AGENT_CREATE.value
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
