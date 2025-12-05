"""
Workflow Service - Manages workflow execution and status tracking

Now uses StorageService for persistence (Azure Blob Storage or local fallback).

This service handles:
- Listing sections from workflow_config.json
- Running workflow sections using the generic workflow agent
- Tracking task status
- Managing results
"""
import os
import asyncio
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from apps.api.app.models import (
    WorkflowSection, WorkflowRunResponse, WorkflowStatusResponse,
    TaskStatus, QuestionResult, ProjectResults
)
from apps.api.app.services.storage_service import get_storage_service


class WorkflowService:
    """Service for workflow management using StorageService backend"""

    # Track running tasks in memory (in production, use Redis or database)
    _tasks: Dict[str, Dict[str, Any]] = {}

    def __init__(self):
        """Initialize workflow service with storage backend"""
        self.storage = get_storage_service()

    def _get_workflow_config(self, project_id: str) -> Dict:
        """Load workflow config for a project"""
        config = self.storage.read_json(project_id, "workflow_config.json")
        return config if config else {"sections": []}

    def _save_workflow_config(self, project_id: str, config: Dict) -> bool:
        """Save workflow config for a project"""
        return self.storage.write_json(project_id, "workflow_config.json", config)

    def _get_results(self, project_id: str) -> Dict:
        """Load results for a project"""
        results = self.storage.read_json(project_id, "output/results.json")
        return results if results else {"sections": {}}

    def _save_results(self, project_id: str, results: Dict) -> bool:
        """Save results for a project"""
        return self.storage.write_json(project_id, "output/results.json", results)

    def list_sections(self, project_id: str) -> List[WorkflowSection]:
        """List all workflow sections with completion status"""
        config = self._get_workflow_config(project_id)
        results = self._get_results(project_id)

        sections = []

        for section in config.get("sections", []):
            section_id = section.get("id", "")
            section_name = section.get("name", "Unnamed Section")
            questions = section.get("questions", [])
            question_count = len(questions)

            # Count completed questions from results
            completed_count = 0
            section_results = results.get("sections", {}).get(section_id, {})
            questions_results = section_results.get("questions", {})

            for q in questions:
                q_id = q.get("id", "")
                if q_id in questions_results:
                    answer = questions_results[q_id].get("answer", "")
                    if answer and answer.strip() and answer.strip() != "N/A":
                        completed_count += 1

            completion_percentage = (
                (completed_count / question_count * 100) if question_count > 0 else 0
            )

            sections.append(WorkflowSection(
                section_id=section_id,
                section_name=section_name,
                question_count=question_count,
                completed_count=completed_count,
                completion_percentage=round(completion_percentage, 2)
            ))

        return sections

    async def run_section(self, section_id: str, project_id: str) -> WorkflowRunResponse:
        """Start running a workflow section"""
        task_id = str(uuid.uuid4())

        # Get section info
        config = self._get_workflow_config(project_id)
        section = None
        for s in config.get("sections", []):
            if s.get("id") == section_id:
                section = s
                break

        if not section:
            return WorkflowRunResponse(
                task_id=task_id,
                status=TaskStatus.FAILED,
                section_id=section_id,
                project_id=project_id,
                message=f"Section not found: {section_id}"
            )

        question_count = len(section.get("questions", []))

        # Store task info
        self._tasks[task_id] = {
            "task_id": task_id,
            "status": TaskStatus.PENDING,
            "section_id": section_id,
            "project_id": project_id,
            "questions_completed": 0,
            "questions_total": question_count,
            "current_question": None,
            "error": None,
            "started_at": datetime.now().isoformat(),
            "completed_at": None
        }

        # Run workflow in background
        asyncio.create_task(self._execute_workflow(task_id, section_id, project_id))

        return WorkflowRunResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            section_id=section_id,
            project_id=project_id,
            message=f"Workflow section '{section.get('name', section_id)}' queued for execution"
        )

    async def _execute_workflow(self, task_id: str, section_id: str, project_id: str):
        """Execute workflow in background"""
        try:
            # Update status to running
            self._tasks[task_id]["status"] = TaskStatus.RUNNING

            # Set environment variable for project
            os.environ["PRISM_PROJECT_NAME"] = project_id

            print(f"\n[WORKFLOW] ===== STARTING SECTION {section_id} WORKFLOW =====")
            print(f"[WORKFLOW] Project: {project_id}")
            print(f"[WORKFLOW] Environment:")
            print(f"[WORKFLOW]   PRISM_PROJECT_NAME={os.environ.get('PRISM_PROJECT_NAME', 'NOT SET')}")
            print(f"[WORKFLOW]   AZURE_SEARCH_ENDPOINT={os.environ.get('AZURE_SEARCH_ENDPOINT', 'NOT SET')}")
            print(f"[WORKFLOW]   AZURE_SEARCH_INDEX_NAME={os.environ.get('AZURE_SEARCH_INDEX_NAME', 'NOT SET')}")
            print(f"[WORKFLOW] Starting execution...\n")

            # Import and create workflow
            from workflows.workflow_agent import WorkflowAgentFactory

            factory = WorkflowAgentFactory(project_id)
            workflow = factory.build_section_workflow(section_id)

            # Start a background task to poll for progress
            async def update_progress():
                while self._tasks[task_id]["status"] == TaskStatus.RUNNING:
                    results = self._get_results(project_id)
                    section_results = results.get("sections", {}).get(section_id, {})
                    questions_results = section_results.get("questions", {})
                    self._tasks[task_id]["questions_completed"] = len(questions_results)
                    await asyncio.sleep(2)

            progress_task = asyncio.create_task(update_progress())

            # Run the workflow
            try:
                result = await workflow.run("Start workflow")
                print(f"\n[WORKFLOW] ===== SECTION {section_id} COMPLETED SUCCESSFULLY =====\n")
            except Exception as e:
                import traceback
                print(f"\n[WORKFLOW] ===== SECTION {section_id} FAILED =====")
                print(f"[WORKFLOW] Error: {e}")
                print(traceback.format_exc())
                raise

            # Cancel progress polling
            progress_task.cancel()
            try:
                await progress_task
            except asyncio.CancelledError:
                pass

            # Final count
            results = self._get_results(project_id)
            section_results = results.get("sections", {}).get(section_id, {})
            questions_results = section_results.get("questions", {})
            self._tasks[task_id]["questions_completed"] = len(questions_results)

            # Update task status
            self._tasks[task_id]["status"] = TaskStatus.COMPLETED
            self._tasks[task_id]["completed_at"] = datetime.now().isoformat()

        except Exception as e:
            print(f"Error executing workflow: {e}")
            self._tasks[task_id]["status"] = TaskStatus.FAILED
            self._tasks[task_id]["error"] = str(e)
            self._tasks[task_id]["completed_at"] = datetime.now().isoformat()

    def get_task_status(self, task_id: str) -> Optional[WorkflowStatusResponse]:
        """Get status of a running workflow task"""
        task_info = self._tasks.get(task_id)

        if not task_info:
            return None

        return WorkflowStatusResponse(
            task_id=task_info["task_id"],
            status=task_info["status"],
            section_id=task_info["section_id"],
            project_id=task_info["project_id"],
            questions_completed=task_info["questions_completed"],
            questions_total=task_info["questions_total"],
            current_question=task_info["current_question"],
            error=task_info["error"],
            started_at=task_info["started_at"],
            completed_at=task_info["completed_at"]
        )

    def get_project_results(self, project_id: str) -> Optional[ProjectResults]:
        """Get all results for a project"""
        results = self._get_results(project_id)
        config = self._get_workflow_config(project_id)

        if not results.get("sections"):
            return None

        sections_data = []
        total_questions = 0
        answered_questions = 0

        # Iterate over config sections to preserve order
        for section in config.get("sections", []):
            section_id = section.get("id", "")
            section_name = section.get("name", "Unnamed")
            questions = section.get("questions", [])

            section_results = results.get("sections", {}).get(section_id, {})
            questions_results = section_results.get("questions", {})

            section_data = {
                "section_id": section_id,
                "section_name": section_name,
                "questions": []
            }

            for q in questions:
                q_id = q.get("id", "")
                q_text = q.get("question", "")
                total_questions += 1

                q_result = questions_results.get(q_id, {})
                answer = q_result.get("answer", "")
                reference = q_result.get("reference", "")
                comments = q_result.get("comments", "")
                evaluation = q_result.get("evaluation", None)

                if answer and answer.strip():
                    answered_questions += 1

                section_data["questions"].append({
                    "question_id": q_id,
                    "question_name": q_text,
                    "answer": answer if answer else None,
                    "reference": reference if reference else None,
                    "comments": comments if comments else None,
                    "evaluation": evaluation
                })

            sections_data.append(section_data)

        return ProjectResults(
            project_id=project_id,
            total_questions=total_questions,
            answered_questions=answered_questions,
            sections=sections_data
        )

    def get_section_questions(self, project_id: str, section_id: str) -> List[Dict[str, Any]]:
        """Get all questions for a specific section"""
        config = self._get_workflow_config(project_id)

        for section in config.get("sections", []):
            if section.get("id") == section_id:
                return section.get("questions", [])

        return []

    def get_section(self, project_id: str, section_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific section by ID"""
        config = self._get_workflow_config(project_id)

        for section in config.get("sections", []):
            if section.get("id") == section_id:
                return section

        return None

    def create_section(self, project_id: str, section_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new section"""
        config = self._get_workflow_config(project_id)

        # Generate ID if not provided
        if "id" not in section_data:
            section_data["id"] = f"section_{len(config.get('sections', [])) + 1}"

        # Ensure questions list exists
        if "questions" not in section_data:
            section_data["questions"] = []

        config.setdefault("sections", []).append(section_data)

        if self._save_workflow_config(project_id, config):
            return section_data
        return None

    def update_section(self, project_id: str, section_id: str, section_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing section"""
        config = self._get_workflow_config(project_id)

        for i, section in enumerate(config.get("sections", [])):
            if section.get("id") == section_id:
                # Preserve ID
                section_data["id"] = section_id
                # Preserve questions if not provided
                if "questions" not in section_data:
                    section_data["questions"] = section.get("questions", [])
                config["sections"][i] = section_data

                if self._save_workflow_config(project_id, config):
                    return section_data
                return None

        return None

    def delete_section(self, project_id: str, section_id: str) -> bool:
        """Delete a section"""
        config = self._get_workflow_config(project_id)

        original_len = len(config.get("sections", []))
        config["sections"] = [s for s in config.get("sections", []) if s.get("id") != section_id]

        if len(config["sections"]) < original_len:
            return self._save_workflow_config(project_id, config)

        return False

    def add_question(self, project_id: str, section_id: str, question_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Add a question to a section"""
        config = self._get_workflow_config(project_id)

        for section in config.get("sections", []):
            if section.get("id") == section_id:
                # Generate ID if not provided
                if "id" not in question_data:
                    question_data["id"] = f"q{len(section.get('questions', [])) + 1}"

                section.setdefault("questions", []).append(question_data)

                if self._save_workflow_config(project_id, config):
                    return question_data
                return None

        return None

    def update_question(self, project_id: str, section_id: str, question_id: str, question_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a question"""
        config = self._get_workflow_config(project_id)

        for section in config.get("sections", []):
            if section.get("id") == section_id:
                for i, q in enumerate(section.get("questions", [])):
                    if q.get("id") == question_id:
                        # Merge with existing question data to preserve fields not being updated
                        updated_question = {**q, **question_data}
                        updated_question["id"] = question_id  # Ensure ID is preserved
                        section["questions"][i] = updated_question

                        if self._save_workflow_config(project_id, config):
                            return updated_question
                        return None

        return None

    def delete_question(self, project_id: str, section_id: str, question_id: str) -> bool:
        """Delete a question from a section"""
        config = self._get_workflow_config(project_id)

        for section in config.get("sections", []):
            if section.get("id") == section_id:
                original_len = len(section.get("questions", []))
                section["questions"] = [q for q in section.get("questions", []) if q.get("id") != question_id]

                if len(section["questions"]) < original_len:
                    return self._save_workflow_config(project_id, config)

        return False

    def update_section_questions(self, project_id: str, section_id: str, questions: List[Dict[str, Any]]) -> bool:
        """Replace all questions in a section with new questions (for CSV import)"""
        config = self._get_workflow_config(project_id)

        for section in config.get("sections", []):
            if section.get("id") == section_id:
                section["questions"] = questions
                return self._save_workflow_config(project_id, config)

        return False

    def clear_section_answers(self, project_id: str, section_id: str) -> int:
        """Clear all answers for a section"""
        results = self._get_results(project_id)

        if section_id not in results.get("sections", {}):
            return 0

        cleared_count = len(results["sections"][section_id].get("questions", {}))
        results["sections"][section_id]["questions"] = {}

        if self._save_results(project_id, results):
            return cleared_count
        return 0
