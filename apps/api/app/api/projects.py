"""
Projects API - List and manage projects, files, and pipeline
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from apps.api.app.models import ProjectInfo
from apps.api.app.services.project_service import ProjectService


router = APIRouter()
project_service = ProjectService()


# ==================== Request Models ====================

class CreateProjectRequest(BaseModel):
    name: str


class SectionRequest(BaseModel):
    id: Optional[str] = None
    name: str
    template: Optional[str] = ""


class QuestionRequest(BaseModel):
    id: Optional[str] = None
    question: str
    instructions: Optional[str] = ""


# ==================== Project CRUD ====================

@router.get("", response_model=List[ProjectInfo])
async def list_projects():
    """List all available projects"""
    try:
        projects = project_service.list_projects()
        return projects
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_project(request: CreateProjectRequest):
    """Create a new project"""
    try:
        # Validate project name (alphanumeric, underscores, hyphens only)
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', request.name):
            raise HTTPException(
                status_code=400,
                detail="Project name can only contain letters, numbers, underscores, and hyphens"
            )

        success = project_service.create_project(request.name)
        if not success:
            raise HTTPException(status_code=400, detail=f"Project '{request.name}' already exists")

        return {"message": f"Project '{request.name}' created successfully", "name": request.name}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}", response_model=ProjectInfo)
async def get_project(project_id: str):
    """Get detailed information about a specific project"""
    try:
        project = project_service.get_project_info(project_id)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
        return project
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """Delete a project and all its contents"""
    try:
        if not project_service.project_exists(project_id):
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

        success = project_service.delete_project(project_id)
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to delete project '{project_id}'")

        return {"message": f"Project '{project_id}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== File Management ====================

@router.get("/{project_id}/files")
async def list_files(project_id: str):
    """List all files in project's documents directory"""
    try:
        if not project_service.project_exists(project_id):
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

        files = project_service.list_files(project_id)
        return {"files": files, "count": len(files)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/files")
async def upload_file(project_id: str, file: UploadFile = File(...)):
    """Upload a file to project's documents directory"""
    try:
        if not project_service.project_exists(project_id):
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

        content = await file.read()
        saved_file = project_service.save_file(project_id, file.filename, content)

        return {"message": "File uploaded successfully", "file": saved_file}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}/files/{filename}")
async def delete_file(project_id: str, filename: str):
    """Delete a file from project's documents directory"""
    try:
        if not project_service.project_exists(project_id):
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

        success = project_service.delete_file(project_id, filename)
        if not success:
            raise HTTPException(status_code=404, detail=f"File '{filename}' not found")

        return {"message": f"File '{filename}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Pipeline Status ====================

@router.get("/{project_id}/status")
async def get_pipeline_status(project_id: str):
    """Get the pipeline status for a project"""
    try:
        if not project_service.project_exists(project_id):
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

        status = project_service.get_pipeline_status(project_id)
        return status
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Workflow Sections CRUD ====================

@router.get("/{project_id}/sections")
async def list_sections(project_id: str):
    """List all sections in project's workflow config"""
    try:
        if not project_service.project_exists(project_id):
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

        sections = project_service.get_sections(project_id)
        return sections
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/sections")
async def create_section(project_id: str, request: SectionRequest):
    """Create a new section in project's workflow config"""
    try:
        if not project_service.project_exists(project_id):
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

        section = project_service.create_section(project_id, {
            "id": request.id,
            "name": request.name,
            "template": request.template or "",
            "questions": []
        })
        return section
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{project_id}/sections/{section_id}")
async def update_section(project_id: str, section_id: str, request: SectionRequest):
    """Update a section in project's workflow config"""
    try:
        if not project_service.project_exists(project_id):
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

        section = project_service.update_section(project_id, section_id, {
            "name": request.name,
            "template": request.template or ""
        })
        if not section:
            raise HTTPException(status_code=404, detail=f"Section '{section_id}' not found")
        return section
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}/sections/{section_id}")
async def delete_section(project_id: str, section_id: str):
    """Delete a section from project's workflow config"""
    try:
        if not project_service.project_exists(project_id):
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

        success = project_service.delete_section(project_id, section_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Section '{section_id}' not found")

        return {"message": f"Section '{section_id}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Section Questions CRUD ====================

@router.get("/{project_id}/sections/{section_id}/questions")
async def list_questions(project_id: str, section_id: str):
    """List all questions in a section"""
    try:
        if not project_service.project_exists(project_id):
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

        questions = project_service.get_questions(project_id, section_id)
        if questions is None:
            raise HTTPException(status_code=404, detail=f"Section '{section_id}' not found")
        return questions
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/sections/{section_id}/questions")
async def create_question(project_id: str, section_id: str, request: QuestionRequest):
    """Create a new question in a section"""
    try:
        if not project_service.project_exists(project_id):
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

        question = project_service.create_question(project_id, section_id, {
            "id": request.id,
            "question": request.question,
            "instructions": request.instructions or ""
        })
        if question is None:
            raise HTTPException(status_code=404, detail=f"Section '{section_id}' not found")
        return question
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{project_id}/sections/{section_id}/questions/{question_id}")
async def update_question(project_id: str, section_id: str, question_id: str, request: QuestionRequest):
    """Update a question in a section"""
    try:
        if not project_service.project_exists(project_id):
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

        question = project_service.update_question(project_id, section_id, question_id, {
            "question": request.question,
            "instructions": request.instructions or ""
        })
        if question is None:
            raise HTTPException(status_code=404, detail=f"Question '{question_id}' not found in section '{section_id}'")
        return question
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}/sections/{section_id}/questions/{question_id}")
async def delete_question(project_id: str, section_id: str, question_id: str):
    """Delete a question from a section"""
    try:
        if not project_service.project_exists(project_id):
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

        success = project_service.delete_question(project_id, section_id, question_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Question '{question_id}' not found in section '{section_id}'")

        return {"message": f"Question '{question_id}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Workflow Export/Import ====================

@router.get("/{project_id}/workflow/export")
async def export_workflow(project_id: str):
    """Export the entire workflow configuration as JSON"""
    try:
        if not project_service.project_exists(project_id):
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

        workflow = project_service.get_workflow_config(project_id)
        if not workflow:
            raise HTTPException(status_code=404, detail=f"No workflow configuration found for project '{project_id}'")

        return workflow
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/workflow/import")
async def import_workflow(project_id: str, workflow: Dict[str, Any]):
    """Import a workflow configuration from JSON"""
    try:
        if not project_service.project_exists(project_id):
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

        # Validate the workflow structure
        if "sections" not in workflow:
            raise HTTPException(status_code=400, detail="Invalid workflow format: 'sections' key is required")

        if not isinstance(workflow["sections"], list):
            raise HTTPException(status_code=400, detail="Invalid workflow format: 'sections' must be a list")

        # Validate each section
        for section in workflow["sections"]:
            if not isinstance(section, dict):
                raise HTTPException(status_code=400, detail="Invalid workflow format: each section must be an object")
            if "id" not in section or "name" not in section:
                raise HTTPException(status_code=400, detail="Invalid workflow format: each section must have 'id' and 'name'")

        success = project_service.save_workflow_config(project_id, workflow)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save workflow configuration")

        section_count = len(workflow["sections"])
        question_count = sum(len(s.get("questions", [])) for s in workflow["sections"])

        return {
            "message": f"Workflow imported successfully",
            "sections_imported": section_count,
            "questions_imported": question_count
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
