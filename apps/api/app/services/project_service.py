"""
Project Service - Manages project information, files, and pipeline status

Uses Azure Blob Storage for all persistence.
"""
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from apps.api.app.models import ProjectInfo
from apps.api.app.services.storage_service import get_storage_service
from scripts.logging_config import get_logger

logger = get_logger(__name__)


class ProjectService:
    """Service for project management using StorageService backend"""

    def __init__(self):
        """Initialize project service with storage backend"""
        self.storage = get_storage_service()

    def list_projects(self) -> List[ProjectInfo]:
        """List all available projects"""
        projects = []
        project_names = self.storage.list_projects()

        for project_name in project_names:
            project_info = self.get_project_info(project_name)
            if project_info:
                projects.append(project_info)

        return sorted(projects, key=lambda p: p.name)

    def get_project_info(self, project_name: str) -> Optional[ProjectInfo]:
        """Get detailed information about a specific project"""
        if not self.storage.project_exists(project_name):
            return None

        # Count documents
        document_files = self.storage.list_files(project_name, "documents")
        document_count = len(document_files)

        # Check output directories by listing files
        extraction_files = self.storage.list_files(project_name, "output/extraction_results")
        has_extraction_results = len(extraction_files) > 0

        chunked_files = self.storage.list_files(project_name, "output/chunked_documents")
        has_chunked_documents = len(chunked_files) > 0

        embedded_files = self.storage.list_files(project_name, "output/embedded_documents")
        has_embedded_documents = len(embedded_files) > 0

        # Check for results.csv
        has_results_csv = self.storage.file_exists(project_name, "output/results.csv")

        # Get last modified time from config
        config = self.storage.read_json(project_name, "config.json")
        last_modified = config.get("last_modified") if config else None

        return ProjectInfo(
            name=project_name,
            document_count=document_count,
            has_extraction_results=has_extraction_results,
            has_chunked_documents=has_chunked_documents,
            has_embedded_documents=has_embedded_documents,
            has_results_csv=has_results_csv,
            last_modified=last_modified
        )

    def project_exists(self, project_name: str) -> bool:
        """Check if a project exists"""
        return self.storage.project_exists(project_name)

    def create_project(self, project_name: str) -> bool:
        """Create a new project with the standard directory structure"""
        return self.storage.create_project(project_name)

    def delete_project(self, project_name: str) -> bool:
        """Delete a project and all its contents, including Azure resources"""
        # First, clean up Azure resources (index, knowledge source, agent)
        try:
            from apps.api.app.services.rollback_service import RollbackService
            rollback_service = RollbackService()

            # Roll back from extraction (cascades to all stages including Azure resources)
            result = rollback_service.rollback_stage(project_name, "extraction", cascade=True)
            if not result.success:
                logger.warning(f"Rollback had errors for project '{project_name}': {result.errors}")
            else:
                logger.info(f"Cleaned up Azure resources for project '{project_name}': {result.deleted_resources}")
        except Exception as e:
            # Log but continue - we still want to delete the blob files
            logger.warning(f"Error cleaning up Azure resources for project '{project_name}': {e}")

        # Then delete all blob files
        return self.storage.delete_project(project_name)

    # ==================== File Management ====================

    def list_files(self, project_name: str) -> List[Dict[str, Any]]:
        """List all files in a project's documents directory"""
        return self.storage.list_files(project_name, "documents")

    def save_file(self, project_name: str, filename: str, content: bytes) -> Dict[str, Any]:
        """Save an uploaded file to the project's documents directory"""
        # Sanitize filename (remove path components)
        safe_filename = os.path.basename(filename)
        relative_path = f"documents/{safe_filename}"

        success = self.storage.write_file(project_name, relative_path, content)

        if success:
            return {
                "name": safe_filename,
                "path": safe_filename,
                "size": len(content),
                "modified": datetime.utcnow().isoformat()
            }
        else:
            raise Exception(f"Failed to save file: {safe_filename}")

    def delete_file(self, project_name: str, filename: str) -> bool:
        """Delete a file from the project's documents directory"""
        # Sanitize to prevent path traversal
        safe_filename = os.path.basename(filename)
        relative_path = f"documents/{safe_filename}"
        return self.storage.delete_file(project_name, relative_path)

    # ==================== Pipeline Status ====================

    def get_pipeline_status(self, project_name: str) -> Dict[str, Any]:
        """Get the pipeline status for a project"""
        # Count documents
        document_files = self.storage.list_files(project_name, "documents")
        document_count = len(document_files)

        # Count extraction results (look for _markdown.md files)
        extraction_files = self.storage.list_files(project_name, "output/extraction_results")
        extraction_count = len([f for f in extraction_files if f["name"].endswith("_markdown.md")])

        # Count chunked documents
        chunked_files = self.storage.list_files(project_name, "output/chunked_documents")
        chunk_count = len([f for f in chunked_files if f["name"].endswith(".json")])

        # Count embedded documents
        embedded_files = self.storage.list_files(project_name, "output/embedded_documents")
        embedded_count = len([f for f in embedded_files if f["name"].endswith(".json")])

        # Determine pipeline stage
        has_documents = document_count > 0
        is_processed = extraction_count > 0 and extraction_count >= document_count
        is_chunked = chunk_count > 0
        is_embedded = embedded_count > 0 and embedded_count >= chunk_count

        # Check if indexed (from config)
        config = self.storage.read_json(project_name, "config.json") or {}
        status = config.get("status", {})
        is_indexed = status.get("is_indexed", False)
        has_agent = status.get("has_agent", False)

        return {
            "project_name": project_name,
            "documents": {
                "count": document_count,
                "has_documents": has_documents
            },
            "extraction": {
                "count": extraction_count,
                "is_processed": is_processed
            },
            "chunking": {
                "count": chunk_count,
                "is_chunked": is_chunked
            },
            "embedding": {
                "count": embedded_count,
                "is_embedded": is_embedded
            },
            "index": {
                "is_indexed": is_indexed
            },
            "agent": {
                "has_agent": has_agent
            },
            "ready_for_query": is_indexed and has_agent
        }

    def update_project_status(self, project_name: str, status_updates: Dict[str, Any]) -> bool:
        """Update the status fields in project config"""
        config = self.storage.read_json(project_name, "config.json")
        if config is None:
            return False

        if "status" not in config:
            config["status"] = {}

        config["status"].update(status_updates)
        return self.storage.write_json(project_name, "config.json", config)

    # ==================== Workflow Config CRUD ====================

    def _load_workflow_config(self, project_name: str) -> Dict:
        """Load workflow config for a project"""
        config = self.storage.read_json(project_name, "workflow_config.json")
        return config if config else {"sections": []}

    def _save_workflow_config(self, project_name: str, config: Dict) -> bool:
        """Save workflow config for a project"""
        return self.storage.write_json(project_name, "workflow_config.json", config)

    def get_sections(self, project_name: str) -> List[Dict]:
        """Get all sections from project's workflow config"""
        config = self._load_workflow_config(project_name)
        return config.get("sections", [])

    def create_section(self, project_name: str, section_data: Dict) -> Dict:
        """Create a new section in project's workflow config"""
        config = self._load_workflow_config(project_name)
        sections = config.get("sections", [])

        # Check for duplicate ID
        section_id = section_data.get("id")
        if any(s.get("id") == section_id for s in sections):
            raise ValueError(f"Section with ID '{section_id}' already exists")

        # Add new section
        new_section = {
            "id": section_id,
            "name": section_data.get("name", ""),
            "template": section_data.get("template", ""),
            "questions": section_data.get("questions", [])
        }
        sections.append(new_section)
        config["sections"] = sections
        self._save_workflow_config(project_name, config)
        return new_section

    def update_section(self, project_name: str, section_id: str, updates: Dict) -> Optional[Dict]:
        """Update a section in project's workflow config"""
        config = self._load_workflow_config(project_name)
        sections = config.get("sections", [])

        for section in sections:
            if section.get("id") == section_id:
                section["name"] = updates.get("name", section.get("name", ""))
                section["template"] = updates.get("template", section.get("template", ""))
                config["sections"] = sections
                self._save_workflow_config(project_name, config)
                return section

        return None

    def delete_section(self, project_name: str, section_id: str) -> bool:
        """Delete a section from project's workflow config"""
        config = self._load_workflow_config(project_name)
        sections = config.get("sections", [])

        original_count = len(sections)
        sections = [s for s in sections if s.get("id") != section_id]

        if len(sections) == original_count:
            return False

        config["sections"] = sections
        self._save_workflow_config(project_name, config)
        return True

    # ==================== Section Questions CRUD ====================

    def get_questions(self, project_name: str, section_id: str) -> Optional[List[Dict]]:
        """Get all questions for a section"""
        config = self._load_workflow_config(project_name)
        sections = config.get("sections", [])

        for section in sections:
            if section.get("id") == section_id:
                return section.get("questions", [])

        return None

    def create_question(self, project_name: str, section_id: str, question_data: Dict) -> Optional[Dict]:
        """Create a new question in a section"""
        config = self._load_workflow_config(project_name)
        sections = config.get("sections", [])

        for section in sections:
            if section.get("id") == section_id:
                questions = section.get("questions", [])

                # Check for duplicate ID
                question_id = question_data.get("id")
                if any(q.get("id") == question_id for q in questions):
                    raise ValueError(f"Question with ID '{question_id}' already exists in section '{section_id}'")

                # Add new question
                new_question = {
                    "id": question_id,
                    "question": question_data.get("question", ""),
                    "instructions": question_data.get("instructions", "")
                }
                questions.append(new_question)
                section["questions"] = questions
                config["sections"] = sections
                self._save_workflow_config(project_name, config)
                return new_question

        return None

    def update_question(self, project_name: str, section_id: str, question_id: str, updates: Dict) -> Optional[Dict]:
        """Update a question in a section"""
        config = self._load_workflow_config(project_name)
        sections = config.get("sections", [])

        for section in sections:
            if section.get("id") == section_id:
                questions = section.get("questions", [])
                for question in questions:
                    if question.get("id") == question_id:
                        # Update only provided fields
                        if "question" in updates:
                            question["question"] = updates["question"]
                        if "instructions" in updates:
                            question["instructions"] = updates["instructions"]
                        if "order" in updates:
                            question["order"] = updates["order"]
                        config["sections"] = sections
                        self._save_workflow_config(project_name, config)
                        return question
                return None

        return None

    def delete_question(self, project_name: str, section_id: str, question_id: str) -> bool:
        """Delete a question from a section"""
        config = self._load_workflow_config(project_name)
        sections = config.get("sections", [])

        for section in sections:
            if section.get("id") == section_id:
                questions = section.get("questions", [])
                original_count = len(questions)
                questions = [q for q in questions if q.get("id") != question_id]

                if len(questions) == original_count:
                    return False

                section["questions"] = questions
                config["sections"] = sections
                self._save_workflow_config(project_name, config)
                return True

        return False

    # ==================== Workflow Export/Import ====================

    def get_workflow_config(self, project_name: str) -> Optional[Dict]:
        """Get the complete workflow configuration for export"""
        return self._load_workflow_config(project_name)

    def save_workflow_config(self, project_name: str, config: Dict) -> bool:
        """Save a complete workflow configuration (for import)"""
        return self._save_workflow_config(project_name, config)

