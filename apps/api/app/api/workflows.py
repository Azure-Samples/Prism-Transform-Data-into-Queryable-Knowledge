"""
Workflows API - Manage and execute workflow sections
"""
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
from typing import List, Optional
from apps.api.app.models import (
    WorkflowSection, WorkflowRunRequest, WorkflowRunResponse,
    WorkflowStatusResponse, ProjectResults
)
from apps.api.app.services.workflow_service import WorkflowService
from apps.api.app.services.project_service import ProjectService
import os


router = APIRouter()
workflow_service = WorkflowService()
project_service = ProjectService()


@router.get("", response_model=List[WorkflowSection])
async def list_workflows(project_id: str = Query(..., description="Project ID to check completion status")):
    """List all workflow sections with completion status"""
    try:
        if not project_service.project_exists(project_id):
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
        sections = workflow_service.list_sections(project_id)
        return sections
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{section_id}/run", response_model=WorkflowRunResponse)
async def run_workflow(section_id: str, request: WorkflowRunRequest):
    """Start executing a workflow section"""
    try:
        # Validate project exists
        if not project_service.project_exists(request.project_id):
            raise HTTPException(status_code=404, detail=f"Project '{request.project_id}' not found")

        # Validate section exists in project
        section = workflow_service.get_section(request.project_id, section_id)
        if not section:
            raise HTTPException(status_code=404, detail=f"Section '{section_id}' not found in project")

        # Start workflow execution
        response = await workflow_service.run_section(section_id, request.project_id)
        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{section_id}/status/{task_id}", response_model=WorkflowStatusResponse)
async def get_workflow_status(section_id: str, task_id: str):
    """Get status of a running workflow"""
    try:
        status = workflow_service.get_task_status(task_id)
        if not status:
            raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
        return status
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results/{project_id}", response_model=ProjectResults)
async def get_results(project_id: str):
    """Get all workflow results for a project"""
    try:
        if not project_service.project_exists(project_id):
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

        results = workflow_service.get_project_results(project_id)
        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"No results found for project '{project_id}'. Run workflows first."
            )
        return results
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results/{project_id}/export")
async def export_results(project_id: str):
    """Export results as CSV file"""
    try:
        if not project_service.project_exists(project_id):
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

        results_path = project_service.get_results_csv_path(project_id)

        if not os.path.exists(results_path):
            raise HTTPException(
                status_code=404,
                detail=f"No results file found for project '{project_id}'"
            )

        return FileResponse(
            results_path,
            media_type='text/csv',
            filename=f'{project_id}_results.csv'
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{section_id}/questions")
async def get_section_questions(section_id: str):
    """Get questions for a specific section"""
    try:
        questions = workflow_service.get_section_questions(section_id)
        return questions
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{section_id}/questions")
async def update_section_questions(section_id: str, questions: List[dict]):
    """Update questions for a specific section"""
    try:
        workflow_service.update_section_questions(section_id, questions)
        return {"status": "success", "message": f"Updated {len(questions)} questions for section {section_id}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{section_id}/questions/export")
async def export_section_questions(section_id: str, project_id: str = Query(..., description="Project ID")):
    """Export questions for a section as CSV file"""
    try:
        import io
        import csv as csv_module
        from fastapi.responses import StreamingResponse

        # Get questions from the workflow config
        questions = workflow_service.get_section_questions(project_id, section_id)
        if questions is None:
            raise HTTPException(status_code=404, detail=f"Section '{section_id}' not found in project")

        # Create CSV in memory
        output = io.StringIO()
        writer = csv_module.DictWriter(output, fieldnames=['id', 'order', 'question', 'instructions'])
        writer.writeheader()

        for q in questions:
            writer.writerow({
                'id': q.get('id', ''),
                'order': q.get('order', ''),
                'question': q.get('question', ''),
                'instructions': q.get('instructions', '')
            })

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type='text/csv',
            headers={'Content-Disposition': f'attachment; filename="{section_id}_questions.csv"'}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{section_id}/questions/import")
async def import_section_questions(
    section_id: str,
    project_id: str = Query(..., description="Project ID"),
    file: UploadFile = File(...)
):
    """Import questions for a section from CSV file"""
    try:
        import io
        import csv as csv_module

        # Read and parse CSV from uploaded file
        content = await file.read()
        csv_content = content.decode('utf-8')
        csv_file = io.StringIO(csv_content)
        reader = csv_module.DictReader(csv_file)

        questions = []
        for row in reader:
            question = {
                'id': row.get('id', ''),
                'question': row.get('question', ''),
                'instructions': row.get('instructions', '')
            }
            # Handle order field if present
            if row.get('order'):
                try:
                    question['order'] = int(row.get('order'))
                except ValueError:
                    pass
            questions.append(question)

        if not questions:
            raise HTTPException(status_code=400, detail="No valid questions found in CSV file")

        # Update questions in the workflow config
        workflow_service.update_section_questions(project_id, section_id, questions)

        return {"status": "success", "message": f"Imported {len(questions)} questions for section {section_id}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{section_id}/answers/{project_id}")
async def clear_section_answers(section_id: str, project_id: str):
    """Clear all answers for a section in a project"""
    try:
        if not project_service.project_exists(project_id):
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

        cleared_count = workflow_service.clear_section_answers(project_id, section_id)
        return {
            "status": "success",
            "message": f"Cleared {cleared_count} answers for section {section_id}",
            "cleared_count": cleared_count
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
