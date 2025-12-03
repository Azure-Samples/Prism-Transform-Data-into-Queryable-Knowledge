"""
Rollback Service - Manages rollback of pipeline stages

Provides functionality to:
- Delete local output files (extraction, chunks, embeddings)
- Delete Azure resources (index, knowledge source, agent)
- Cascade rollback (rolling back early stage removes later stages)
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RollbackResult:
    """Result of a rollback operation"""
    success: bool
    stage: str
    message: str
    deleted_files: int = 0
    deleted_resources: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class RollbackService:
    """Service for rolling back pipeline stages"""

    # Define cascade dependencies - rolling back a stage also rolls back these
    ROLLBACK_CASCADE = {
        "extraction": ["chunking", "embedding", "index", "source", "agent"],
        "chunking": ["embedding", "index", "source", "agent"],
        "embedding": ["index", "source", "agent"],
        "index": ["source", "agent"],
        "source": ["agent"],
        "agent": []
    }

    # Valid stages that can be rolled back
    VALID_STAGES = ["extraction", "chunking", "embedding", "index", "source", "agent"]

    def __init__(self, base_path: str = None):
        """Initialize rollback service"""
        if base_path is None:
            base_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), '../../../..')
            )
        self.base_path = base_path
        self.projects_dir = os.path.join(base_path, 'projects')

    def _get_project_path(self, project_id: str) -> Path:
        """Get project path"""
        return Path(self.projects_dir) / project_id

    def _get_output_path(self, project_id: str) -> Path:
        """Get output path"""
        return self._get_project_path(project_id) / "output"

    def rollback_stage(
        self,
        project_id: str,
        stage: str,
        cascade: bool = True
    ) -> RollbackResult:
        """
        Roll back a stage and optionally cascade to dependent stages.

        Args:
            project_id: Project name
            stage: Stage to roll back (extraction, chunking, embedding, index, source, agent)
            cascade: If True, also roll back dependent stages

        Returns:
            RollbackResult with success status and details
        """
        if stage not in self.VALID_STAGES:
            return RollbackResult(
                success=False,
                stage=stage,
                message=f"Invalid stage '{stage}'. Valid stages: {self.VALID_STAGES}"
            )

        # Check project exists
        project_path = self._get_project_path(project_id)
        if not project_path.exists():
            return RollbackResult(
                success=False,
                stage=stage,
                message=f"Project '{project_id}' not found"
            )

        # Determine stages to roll back
        stages_to_rollback = [stage]
        if cascade:
            stages_to_rollback.extend(self.ROLLBACK_CASCADE.get(stage, []))

        # Remove duplicates while preserving order
        seen = set()
        unique_stages = []
        for s in stages_to_rollback:
            if s not in seen:
                seen.add(s)
                unique_stages.append(s)
        stages_to_rollback = unique_stages

        # Roll back in reverse order (agent first, then source, then index, etc.)
        # This ensures we delete dependent resources before their dependencies
        results = []
        deleted_resources = []
        errors = []
        total_deleted_files = 0

        for s in reversed(stages_to_rollback):
            result = self._rollback_single_stage(project_id, s)
            results.append(result)

            if result.success:
                deleted_resources.append(s)
                total_deleted_files += result.deleted_files
            else:
                errors.append(f"{s}: {result.message}")

        # Overall success if all stages succeeded
        all_success = all(r.success for r in results)

        return RollbackResult(
            success=all_success,
            stage=stage,
            message=f"Rolled back {len(deleted_resources)} stage(s)" if all_success else f"Rollback completed with errors",
            deleted_files=total_deleted_files,
            deleted_resources=deleted_resources,
            errors=errors
        )

    def _rollback_single_stage(self, project_id: str, stage: str) -> RollbackResult:
        """Roll back a single stage without cascade"""
        handlers = {
            "extraction": self._rollback_extraction,
            "chunking": self._rollback_chunking,
            "embedding": self._rollback_embedding,
            "index": self._rollback_index,
            "source": self._rollback_source,
            "agent": self._rollback_agent
        }

        handler = handlers.get(stage)
        if handler:
            return handler(project_id)

        return RollbackResult(
            success=False,
            stage=stage,
            message=f"No handler for stage: {stage}"
        )

    def _rollback_extraction(self, project_id: str) -> RollbackResult:
        """Delete extraction_results directory"""
        output_path = self._get_output_path(project_id)
        extraction_path = output_path / "extraction_results"

        result = self._delete_directory(extraction_path, "extraction")

        # Also delete document_inventory.json if it exists (from deduplication)
        inventory_path = output_path / "document_inventory.json"
        if inventory_path.exists():
            try:
                inventory_path.unlink()
                result.deleted_files += 1
            except Exception:
                pass

        return result

    def _rollback_chunking(self, project_id: str) -> RollbackResult:
        """Delete chunked_documents directory"""
        path = self._get_output_path(project_id) / "chunked_documents"
        return self._delete_directory(path, "chunking")

    def _rollback_embedding(self, project_id: str) -> RollbackResult:
        """Delete embedded_documents directory"""
        output_path = self._get_output_path(project_id)
        embedded_path = output_path / "embedded_documents"

        result = self._delete_directory(embedded_path, "embedding")

        # Also delete indexing_reports if they exist
        reports_path = output_path / "indexing_reports"
        if reports_path.exists():
            try:
                file_count = len(list(reports_path.glob("*")))
                shutil.rmtree(reports_path)
                result.deleted_files += file_count
            except Exception:
                pass

        return result

    def _rollback_index(self, project_id: str) -> RollbackResult:
        """Delete Azure AI Search index"""
        os.environ['PRISM_PROJECT_NAME'] = project_id

        try:
            from scripts.search_index import delete_search_index
            exit_code = delete_search_index.main()

            if exit_code == 0:
                # Update project config status
                self._update_project_status(project_id, {"is_indexed": False})
                return RollbackResult(
                    success=True,
                    stage="index",
                    message="Search index deleted"
                )
            else:
                return RollbackResult(
                    success=False,
                    stage="index",
                    message="Failed to delete search index"
                )

        except Exception as e:
            return RollbackResult(
                success=False,
                stage="index",
                message=str(e)
            )

    def _rollback_source(self, project_id: str) -> RollbackResult:
        """Delete knowledge source"""
        os.environ['PRISM_PROJECT_NAME'] = project_id

        try:
            from scripts.search_index import delete_knowledge_source
            exit_code = delete_knowledge_source.main()

            if exit_code == 0:
                return RollbackResult(
                    success=True,
                    stage="source",
                    message="Knowledge source deleted"
                )
            else:
                return RollbackResult(
                    success=False,
                    stage="source",
                    message="Failed to delete knowledge source"
                )

        except Exception as e:
            return RollbackResult(
                success=False,
                stage="source",
                message=str(e)
            )

    def _rollback_agent(self, project_id: str) -> RollbackResult:
        """Delete knowledge agent"""
        os.environ['PRISM_PROJECT_NAME'] = project_id

        try:
            from scripts.search_index import delete_knowledge_agent
            exit_code = delete_knowledge_agent.main()

            if exit_code == 0:
                # Update project config status
                self._update_project_status(project_id, {
                    "has_agent": False,
                    "agent_name": None
                })
                return RollbackResult(
                    success=True,
                    stage="agent",
                    message="Knowledge agent deleted"
                )
            else:
                return RollbackResult(
                    success=False,
                    stage="agent",
                    message="Failed to delete knowledge agent"
                )

        except Exception as e:
            return RollbackResult(
                success=False,
                stage="agent",
                message=str(e)
            )

    def _delete_directory(self, path: Path, stage: str) -> RollbackResult:
        """Delete a directory and return result"""
        if not path.exists():
            return RollbackResult(
                success=True,
                stage=stage,
                message="Directory did not exist",
                deleted_files=0
            )

        try:
            # Count files before deletion
            file_count = sum(1 for _ in path.rglob("*") if _.is_file())

            # Delete the directory
            shutil.rmtree(path)

            return RollbackResult(
                success=True,
                stage=stage,
                message=f"Deleted {file_count} files",
                deleted_files=file_count
            )

        except Exception as e:
            return RollbackResult(
                success=False,
                stage=stage,
                message=f"Failed to delete directory: {e}"
            )

    def _update_project_status(self, project_id: str, updates: Dict[str, Any]) -> bool:
        """Update project config status fields"""
        config_path = self._get_project_path(project_id) / "config.json"

        if not config_path.exists():
            return False

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            if 'status' not in config:
                config['status'] = {}

            config['status'].update(updates)

            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            return True

        except Exception:
            return False

    def get_rollback_preview(self, project_id: str, stage: str, cascade: bool = True) -> Dict[str, Any]:
        """
        Preview what would be deleted by a rollback operation.

        Returns information about files and resources that would be affected.
        """
        if stage not in self.VALID_STAGES:
            return {"error": f"Invalid stage '{stage}'"}

        project_path = self._get_project_path(project_id)
        if not project_path.exists():
            return {"error": f"Project '{project_id}' not found"}

        # Determine stages to roll back
        stages_to_rollback = [stage]
        if cascade:
            stages_to_rollback.extend(self.ROLLBACK_CASCADE.get(stage, []))

        # Remove duplicates
        stages_to_rollback = list(dict.fromkeys(stages_to_rollback))

        preview = {
            "stages": stages_to_rollback,
            "local_files": {},
            "azure_resources": [],
            "warnings": []
        }

        output_path = self._get_output_path(project_id)

        # Check each stage
        for s in stages_to_rollback:
            if s == "extraction":
                path = output_path / "extraction_results"
                if path.exists():
                    file_count = sum(1 for _ in path.rglob("*") if _.is_file())
                    preview["local_files"]["extraction_results"] = file_count

            elif s == "chunking":
                path = output_path / "chunked_documents"
                if path.exists():
                    file_count = sum(1 for _ in path.rglob("*") if _.is_file())
                    preview["local_files"]["chunked_documents"] = file_count

            elif s == "embedding":
                path = output_path / "embedded_documents"
                if path.exists():
                    file_count = sum(1 for _ in path.rglob("*") if _.is_file())
                    preview["local_files"]["embedded_documents"] = file_count

            elif s == "index":
                preview["azure_resources"].append(f"prism-{project_id}-index")

            elif s == "source":
                preview["azure_resources"].append(f"prism-{project_id}-index-source")

            elif s == "agent":
                preview["azure_resources"].append(f"prism-{project_id}-index-agent")

        # Add warnings
        if "index" in stages_to_rollback:
            preview["warnings"].append(
                "Deleting the index will remove all searchable content. "
                "You will need to re-embed and re-upload to restore search functionality."
            )

        if "extraction" in stages_to_rollback:
            preview["warnings"].append(
                "Deleting extraction results will require re-processing all documents."
            )

        return preview
