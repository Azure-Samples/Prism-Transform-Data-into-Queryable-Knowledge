"""
Project Service - Manages project information, files, and pipeline status
"""
import os
import json
import shutil
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pathlib import Path
from apps.api.app.models import ProjectInfo


class ProjectService:
    """Service for project management"""

    def __init__(self, base_path: str = None):
        """Initialize project service"""
        if base_path is None:
            # Get the project root directory (4 levels up from this file)
            base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
        self.base_path = base_path
        self.projects_dir = os.path.join(base_path, 'projects')

    def list_projects(self) -> List[ProjectInfo]:
        """List all available projects"""
        projects = []

        # Scan projects directory for project folders
        if os.path.exists(self.projects_dir):
            for project_name in os.listdir(self.projects_dir):
                project_path = os.path.join(self.projects_dir, project_name)
                if os.path.isdir(project_path) and not project_name.startswith('.'):
                    project_info = self.get_project_info(project_name)
                    if project_info:
                        projects.append(project_info)

        return sorted(projects, key=lambda p: p.name)

    def get_project_info(self, project_name: str) -> Optional[ProjectInfo]:
        """Get detailed information about a specific project"""
        project_path = os.path.join(self.projects_dir, project_name)
        documents_dir = os.path.join(project_path, 'documents')
        output_dir = os.path.join(project_path, 'output')

        # Check if project exists
        if not os.path.exists(project_path):
            return None

        # Count documents
        document_count = 0
        if os.path.exists(documents_dir):
            for root, dirs, files in os.walk(documents_dir):
                document_count += len([f for f in files if not f.startswith('.')])

        # Check output directories
        has_extraction_results = os.path.exists(
            os.path.join(output_dir, 'extraction_results')
        )
        has_chunked_documents = os.path.exists(
            os.path.join(output_dir, 'chunked_documents')
        )
        has_embedded_documents = os.path.exists(
            os.path.join(output_dir, 'embedded_documents')
        )

        results_csv_path = os.path.join(output_dir, 'results.csv')
        has_results_csv = os.path.exists(results_csv_path)

        # Get last modified time
        last_modified = None
        if os.path.exists(output_dir):
            try:
                mtime = os.path.getmtime(output_dir)
                last_modified = datetime.fromtimestamp(mtime).isoformat()
            except Exception:
                pass

        return ProjectInfo(
            name=project_name,
            document_count=document_count,
            has_extraction_results=has_extraction_results,
            has_chunked_documents=has_chunked_documents,
            has_embedded_documents=has_embedded_documents,
            has_results_csv=has_results_csv,
            last_modified=last_modified
        )

    def get_results_csv_path(self, project_name: str) -> str:
        """Get path to results CSV for a project"""
        return os.path.join(self.projects_dir, project_name, 'output', 'results.csv')

    def project_exists(self, project_name: str) -> bool:
        """Check if a project exists"""
        project_path = os.path.join(self.projects_dir, project_name)
        return os.path.exists(project_path) and os.path.isdir(project_path)

    def create_project(self, project_name: str) -> bool:
        """Create a new project with the standard directory structure"""
        project_path = os.path.join(self.projects_dir, project_name)

        if os.path.exists(project_path):
            return False  # Project already exists

        try:
            # Create project directories
            os.makedirs(os.path.join(project_path, 'documents'))
            os.makedirs(os.path.join(project_path, 'output'))

            # Create config.json
            config = {
                "name": project_name,
                "description": "",
                "created_at": datetime.utcnow().isoformat() + "Z",
                "status": {
                    "has_documents": False,
                    "is_processed": False,
                    "is_indexed": False,
                    "has_agent": False
                }
            }
            config_path = os.path.join(project_path, 'config.json')
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)

            # Create empty workflow_config.json
            workflow_config = {
                "sections": []
            }
            workflow_path = os.path.join(project_path, 'workflow_config.json')
            with open(workflow_path, 'w') as f:
                json.dump(workflow_config, f, indent=2)

            return True
        except Exception as e:
            print(f"Error creating project: {e}")
            return False

    def delete_project(self, project_name: str) -> bool:
        """Delete a project and all its contents"""
        project_path = os.path.join(self.projects_dir, project_name)

        if not os.path.exists(project_path):
            return False

        try:
            import shutil
            shutil.rmtree(project_path)
            return True
        except Exception as e:
            print(f"Error deleting project: {e}")
            return False

    def get_documents_path(self, project_name: str) -> str:
        """Get path to documents directory for a project"""
        return os.path.join(self.projects_dir, project_name, 'documents')

    def get_output_path(self, project_name: str) -> str:
        """Get path to output directory for a project"""
        return os.path.join(self.projects_dir, project_name, 'output')

    # ==================== File Management ====================

    def list_files(self, project_name: str) -> List[Dict[str, Any]]:
        """List all files in a project's documents directory"""
        documents_dir = self.get_documents_path(project_name)
        files = []

        if not os.path.exists(documents_dir):
            return files

        for root, dirs, filenames in os.walk(documents_dir):
            for filename in filenames:
                if filename.startswith('.'):
                    continue
                filepath = os.path.join(root, filename)
                rel_path = os.path.relpath(filepath, documents_dir)
                stat = os.stat(filepath)
                files.append({
                    "name": filename,
                    "path": rel_path,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })

        return sorted(files, key=lambda f: f["name"])

    def save_file(self, project_name: str, filename: str, content: bytes) -> Dict[str, Any]:
        """Save an uploaded file to the project's documents directory"""
        documents_dir = self.get_documents_path(project_name)
        os.makedirs(documents_dir, exist_ok=True)

        # Sanitize filename (remove path components)
        safe_filename = os.path.basename(filename)
        filepath = os.path.join(documents_dir, safe_filename)

        with open(filepath, 'wb') as f:
            f.write(content)

        stat = os.stat(filepath)
        return {
            "name": safe_filename,
            "path": safe_filename,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
        }

    def delete_file(self, project_name: str, filename: str) -> bool:
        """Delete a file from the project's documents directory"""
        documents_dir = self.get_documents_path(project_name)
        # Sanitize to prevent path traversal
        safe_filename = os.path.basename(filename)
        filepath = os.path.join(documents_dir, safe_filename)

        if os.path.exists(filepath) and os.path.isfile(filepath):
            os.remove(filepath)
            return True
        return False

    # ==================== Pipeline Status ====================

    def get_pipeline_status(self, project_name: str) -> Dict[str, Any]:
        """Get the pipeline status for a project"""
        project_path = os.path.join(self.projects_dir, project_name)
        documents_dir = os.path.join(project_path, 'documents')
        output_dir = os.path.join(project_path, 'output')

        # Count documents
        document_count = 0
        if os.path.exists(documents_dir):
            for root, dirs, files in os.walk(documents_dir):
                document_count += len([f for f in files if not f.startswith('.')])

        # Check extraction results
        extraction_dir = os.path.join(output_dir, 'extraction_results')
        extraction_count = 0
        if os.path.exists(extraction_dir):
            extraction_count = len([f for f in os.listdir(extraction_dir)
                                   if f.endswith('_markdown.md')])

        # Check chunked documents
        chunks_dir = os.path.join(output_dir, 'chunked_documents')
        chunk_count = 0
        if os.path.exists(chunks_dir):
            chunk_count = len([f for f in os.listdir(chunks_dir) if f.endswith('.json')])

        # Check embedded documents
        embedded_dir = os.path.join(output_dir, 'embedded_documents')
        embedded_count = 0
        if os.path.exists(embedded_dir):
            embedded_count = len([f for f in os.listdir(embedded_dir) if f.endswith('.json')])

        # Determine pipeline stage
        has_documents = document_count > 0
        is_processed = extraction_count > 0
        is_chunked = chunk_count > 0
        is_embedded = embedded_count > 0

        # Check if indexed (we'll check config for this)
        config_path = os.path.join(project_path, 'config.json')
        is_indexed = False
        has_agent = False
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    status = config.get('status', {})
                    is_indexed = status.get('is_indexed', False)
                    has_agent = status.get('has_agent', False)
            except Exception:
                pass

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
        config_path = os.path.join(self.projects_dir, project_name, 'config.json')

        if not os.path.exists(config_path):
            return False

        try:
            with open(config_path, 'r') as f:
                config = json.load(f)

            if 'status' not in config:
                config['status'] = {}

            config['status'].update(status_updates)

            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)

            return True
        except Exception as e:
            print(f"Error updating project status: {e}")
            return False

    # ==================== Workflow Sections CRUD ====================

    def _get_workflow_config_path(self, project_name: str) -> str:
        """Get path to workflow config file"""
        return os.path.join(self.projects_dir, project_name, 'workflow_config.json')

    def _load_workflow_config(self, project_name: str) -> Dict:
        """Load workflow config for a project"""
        config_path = self._get_workflow_config_path(project_name)
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"sections": []}

    def _save_workflow_config(self, project_name: str, config: Dict) -> None:
        """Save workflow config for a project"""
        config_path = self._get_workflow_config_path(project_name)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def get_sections(self, project_name: str) -> List[Dict]:
        """Get all sections from project's workflow config"""
        config = self._load_workflow_config(project_name)
        return config.get('sections', [])

    def create_section(self, project_name: str, section_data: Dict) -> Dict:
        """Create a new section in project's workflow config"""
        config = self._load_workflow_config(project_name)
        sections = config.get('sections', [])

        # Check for duplicate ID
        section_id = section_data.get('id')
        if any(s.get('id') == section_id for s in sections):
            raise ValueError(f"Section with ID '{section_id}' already exists")

        # Add new section
        new_section = {
            "id": section_id,
            "name": section_data.get('name', ''),
            "template": section_data.get('template', ''),
            "questions": section_data.get('questions', [])
        }
        sections.append(new_section)
        config['sections'] = sections
        self._save_workflow_config(project_name, config)
        return new_section

    def update_section(self, project_name: str, section_id: str, updates: Dict) -> Optional[Dict]:
        """Update a section in project's workflow config"""
        config = self._load_workflow_config(project_name)
        sections = config.get('sections', [])

        for section in sections:
            if section.get('id') == section_id:
                section['name'] = updates.get('name', section.get('name', ''))
                section['template'] = updates.get('template', section.get('template', ''))
                config['sections'] = sections
                self._save_workflow_config(project_name, config)
                return section

        return None

    def delete_section(self, project_name: str, section_id: str) -> bool:
        """Delete a section from project's workflow config"""
        config = self._load_workflow_config(project_name)
        sections = config.get('sections', [])

        original_count = len(sections)
        sections = [s for s in sections if s.get('id') != section_id]

        if len(sections) == original_count:
            return False

        config['sections'] = sections
        self._save_workflow_config(project_name, config)
        return True

    # ==================== Section Questions CRUD ====================

    def get_questions(self, project_name: str, section_id: str) -> Optional[List[Dict]]:
        """Get all questions for a section"""
        config = self._load_workflow_config(project_name)
        sections = config.get('sections', [])

        for section in sections:
            if section.get('id') == section_id:
                return section.get('questions', [])

        return None

    def create_question(self, project_name: str, section_id: str, question_data: Dict) -> Optional[Dict]:
        """Create a new question in a section"""
        config = self._load_workflow_config(project_name)
        sections = config.get('sections', [])

        for section in sections:
            if section.get('id') == section_id:
                questions = section.get('questions', [])

                # Check for duplicate ID
                question_id = question_data.get('id')
                if any(q.get('id') == question_id for q in questions):
                    raise ValueError(f"Question with ID '{question_id}' already exists in section '{section_id}'")

                # Add new question
                new_question = {
                    "id": question_id,
                    "question": question_data.get('question', ''),
                    "instructions": question_data.get('instructions', '')
                }
                questions.append(new_question)
                section['questions'] = questions
                config['sections'] = sections
                self._save_workflow_config(project_name, config)
                return new_question

        return None

    def update_question(self, project_name: str, section_id: str, question_id: str, updates: Dict) -> Optional[Dict]:
        """Update a question in a section"""
        config = self._load_workflow_config(project_name)
        sections = config.get('sections', [])

        for section in sections:
            if section.get('id') == section_id:
                questions = section.get('questions', [])
                for question in questions:
                    if question.get('id') == question_id:
                        question['question'] = updates.get('question', question.get('question', ''))
                        question['instructions'] = updates.get('instructions', question.get('instructions', ''))
                        config['sections'] = sections
                        self._save_workflow_config(project_name, config)
                        return question
                return None

        return None

    def delete_question(self, project_name: str, section_id: str, question_id: str) -> bool:
        """Delete a question from a section"""
        config = self._load_workflow_config(project_name)
        sections = config.get('sections', [])

        for section in sections:
            if section.get('id') == section_id:
                questions = section.get('questions', [])
                original_count = len(questions)
                questions = [q for q in questions if q.get('id') != question_id]

                if len(questions) == original_count:
                    return False

                section['questions'] = questions
                config['sections'] = sections
                self._save_workflow_config(project_name, config)
                return True

        return False
