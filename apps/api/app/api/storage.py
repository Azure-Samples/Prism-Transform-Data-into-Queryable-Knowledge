"""
Storage API - Azure Blob Storage management endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from apps.api.app.services.storage_service import get_storage_service

router = APIRouter()


class StorageStatus(BaseModel):
    """Storage status response"""
    blob_enabled: bool
    account_name: Optional[str]
    container_name: Optional[str]
    local_fallback: bool


class SyncRequest(BaseModel):
    """Sync request"""
    project_name: str
    direction: str  # "to_blob" or "from_blob"


class SyncResponse(BaseModel):
    """Sync response"""
    success: bool
    message: str


@router.get("/status", response_model=StorageStatus)
async def get_storage_status():
    """Get current storage configuration status."""
    storage = get_storage_service()

    return StorageStatus(
        blob_enabled=storage.is_blob_enabled,
        account_name=storage.account_name if storage.is_blob_enabled else None,
        container_name=storage.container_name if storage.is_blob_enabled else None,
        local_fallback=not storage.is_blob_enabled
    )


@router.post("/sync", response_model=SyncResponse)
async def sync_project(request: SyncRequest):
    """
    Sync a project between local and blob storage.

    - direction: "to_blob" uploads local project to Azure
    - direction: "from_blob" downloads Azure project to local
    """
    storage = get_storage_service()

    if not storage.is_blob_enabled:
        raise HTTPException(
            status_code=400,
            detail="Azure Blob Storage not configured. Set AZURE_STORAGE_* environment variables."
        )

    if request.direction == "to_blob":
        success = storage.sync_to_blob(request.project_name)
        message = f"Synced '{request.project_name}' to Azure Blob Storage" if success else "Sync failed"
    elif request.direction == "from_blob":
        success = storage.sync_from_blob(request.project_name)
        message = f"Synced '{request.project_name}' from Azure Blob Storage" if success else "Sync failed"
    else:
        raise HTTPException(status_code=400, detail="Invalid direction. Use 'to_blob' or 'from_blob'")

    return SyncResponse(success=success, message=message)


@router.get("/projects")
async def list_blob_projects():
    """List all projects in blob storage."""
    storage = get_storage_service()

    if not storage.is_blob_enabled:
        raise HTTPException(
            status_code=400,
            detail="Azure Blob Storage not configured"
        )

    projects = storage.list_projects()
    return {"projects": projects, "count": len(projects)}
