"""
Rollback API - Manage pipeline rollback operations

Endpoints for rolling back pipeline stages and clearing project output.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from apps.api.app.services.rollback_service import RollbackService
from apps.api.app.services.project_service import ProjectService


router = APIRouter()
rollback_service = RollbackService()
project_service = ProjectService()


# ==================== Response Models ====================

class RollbackResponse(BaseModel):
    success: bool
    stage: str
    message: str
    deleted_files: int = 0
    deleted_stages: List[str] = []
    errors: List[str] = []


class RollbackPreviewResponse(BaseModel):
    stages: List[str]
    local_files: dict
    azure_resources: List[str]
    warnings: List[str]


# ==================== Endpoints ====================

@router.get("/{project_id}/preview/{stage}")
async def preview_rollback(project_id: str, stage: str, cascade: bool = True):
    """
    Preview what would be deleted by a rollback operation.

    Returns information about files and Azure resources that would be affected.
    Use this before confirming a rollback to show the user what will happen.

    Args:
        project_id: Project name
        stage: Stage to roll back (extraction, chunking, embedding, index, source, agent)
        cascade: If True (default), also show dependent stages that will be deleted
    """
    if not project_service.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

    valid_stages = rollback_service.VALID_STAGES
    if stage not in valid_stages:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid stage '{stage}'. Valid stages: {valid_stages}"
        )

    preview = rollback_service.get_rollback_preview(project_id, stage, cascade)

    if "error" in preview:
        raise HTTPException(status_code=400, detail=preview["error"])

    return preview


@router.post("/{project_id}/rollback/{stage}")
async def rollback_stage(project_id: str, stage: str, cascade: bool = True):
    """
    Roll back a specific pipeline stage.

    This will delete the output files and/or Azure resources for the specified stage.
    If cascade=True (default), also rolls back all dependent stages.

    Cascade behavior:
    - extraction: Also deletes chunking, embedding, index, source, agent
    - chunking: Also deletes embedding, index, source, agent
    - embedding: Also deletes index, source, agent
    - index: Also deletes source, agent
    - source: Also deletes agent
    - agent: Only deletes agent

    Args:
        project_id: Project name
        stage: Stage to roll back (extraction, chunking, embedding, index, source, agent)
        cascade: If True (default), also roll back dependent stages
    """
    if not project_service.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

    valid_stages = rollback_service.VALID_STAGES
    if stage not in valid_stages:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid stage '{stage}'. Valid stages: {valid_stages}"
        )

    result = rollback_service.rollback_stage(project_id, stage, cascade)

    return {
        "success": result.success,
        "stage": result.stage,
        "message": result.message,
        "deleted_files": result.deleted_files,
        "deleted_stages": result.deleted_resources,
        "errors": result.errors
    }


@router.delete("/{project_id}/clear-all")
async def clear_all_output(project_id: str):
    """
    Clear all output and Azure resources for a project.

    This is equivalent to rolling back the extraction stage with cascade=True,
    which will delete:
    - All extraction results
    - All chunked documents
    - All embedded documents
    - The Azure AI Search index
    - The knowledge source
    - The knowledge agent

    The original source documents in the 'documents' folder are NOT deleted.

    Args:
        project_id: Project name
    """
    if not project_service.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

    # Roll back from extraction with cascade to delete everything
    result = rollback_service.rollback_stage(project_id, "extraction", cascade=True)

    return {
        "success": result.success,
        "message": "All output cleared" if result.success else "Clear completed with errors",
        "deleted_files": result.deleted_files,
        "deleted_stages": result.deleted_resources,
        "errors": result.errors
    }


@router.post("/{project_id}/rollback-to/{target_stage}")
async def rollback_to_stage(project_id: str, target_stage: str):
    """
    Roll back to a specific stage, keeping that stage and earlier stages intact.

    This will delete all stages AFTER the target stage.

    Examples:
    - rollback-to/extraction: Keeps extraction, deletes chunking, embedding, index, source, agent
    - rollback-to/chunking: Keeps extraction & chunking, deletes embedding, index, source, agent
    - rollback-to/embedding: Keeps extraction, chunking & embedding, deletes index, source, agent

    Args:
        project_id: Project name
        target_stage: The stage to roll back TO (this stage will be kept)
    """
    if not project_service.project_exists(project_id):
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

    valid_stages = rollback_service.VALID_STAGES
    if target_stage not in valid_stages:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid stage '{target_stage}'. Valid stages: {valid_stages}"
        )

    # Find stages after the target
    stage_order = ["extraction", "chunking", "embedding", "index", "source", "agent"]
    target_index = stage_order.index(target_stage)

    # Stages to delete are everything after the target
    stages_to_delete = stage_order[target_index + 1:]

    if not stages_to_delete:
        return {
            "success": True,
            "message": f"Already at stage '{target_stage}', nothing to roll back",
            "deleted_files": 0,
            "deleted_stages": []
        }

    # Roll back from the first stage after target
    # Use cascade=False since we're manually specifying which stages to delete
    first_stage_to_delete = stages_to_delete[0]

    # But we actually want cascade here since we want all following stages
    result = rollback_service.rollback_stage(project_id, first_stage_to_delete, cascade=True)

    return {
        "success": result.success,
        "message": f"Rolled back to '{target_stage}'" if result.success else "Rollback completed with errors",
        "deleted_files": result.deleted_files,
        "deleted_stages": result.deleted_resources,
        "errors": result.errors
    }
