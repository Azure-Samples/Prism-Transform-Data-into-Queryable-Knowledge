"""
Rollback Service - Manages rollback of pipeline stages

Uses Azure Blob Storage exclusively for all file operations.

Provides functionality to:
- Delete output files (extraction, chunks, embeddings) from blob storage
- Delete Azure resources (index, knowledge source, agent)
- Cascade rollback (rolling back early stage removes later stages)
"""

import os
from typing import Dict, List, Any
from dataclasses import dataclass, field

from apps.api.app.services.storage_service import get_storage_service


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
    """Service for rolling back pipeline stages using blob storage"""

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

    def __init__(self):
        """Initialize rollback service with storage backend"""
        self.storage = get_storage_service()

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
        if not self.storage.project_exists(project_id):
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
        stages_to_rollback = list(dict.fromkeys(stages_to_rollback))

        # Roll back in reverse order (agent first, then source, then index, etc.)
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

        all_success = all(r.success for r in results)

        return RollbackResult(
            success=all_success,
            stage=stage,
            message=f"Rolled back {len(deleted_resources)} stage(s)" if all_success else "Rollback completed with errors",
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

    def _delete_blob_directory(self, project_id: str, prefix: str) -> int:
        """Delete all files in a blob directory prefix"""
        deleted = 0
        files = self.storage.list_files(project_id, prefix)
        for f in files:
            # list_files returns paths relative to project, use path directly
            file_path = f.get('path') or f.get('name')
            if self.storage.delete_file(project_id, file_path):
                deleted += 1
        return deleted

    def _rollback_extraction(self, project_id: str) -> RollbackResult:
        """Delete extraction_results from blob storage"""
        deleted_files = self._delete_blob_directory(project_id, "output/extraction_results")

        # Delete auxiliary files
        auxiliary_files = [
            "output/extraction_status.json",
            "output/document_inventory.json",
            "output/deduplication_report.md",
            "output/extraction_analysis.json",
            "output/results.json",  # Workflow answers
        ]

        for file_path in auxiliary_files:
            if self.storage.file_exists(project_id, file_path):
                self.storage.delete_file(project_id, file_path)
                deleted_files += 1

        return RollbackResult(
            success=True,
            stage="extraction",
            message=f"Deleted {deleted_files} files",
            deleted_files=deleted_files
        )

    def _rollback_chunking(self, project_id: str) -> RollbackResult:
        """Delete chunked_documents from blob storage"""
        deleted_files = self._delete_blob_directory(project_id, "output/chunked_documents")

        return RollbackResult(
            success=True,
            stage="chunking",
            message=f"Deleted {deleted_files} files",
            deleted_files=deleted_files
        )

    def _rollback_embedding(self, project_id: str) -> RollbackResult:
        """Delete embedded_documents from blob storage"""
        deleted_files = self._delete_blob_directory(project_id, "output/embedded_documents")
        deleted_files += self._delete_blob_directory(project_id, "output/indexing_reports")

        # Delete embedding-related report files
        report_files = [
            "output/embedding_report.md",
            "output/index_verification.md",
            "output/upload_report.json",
        ]

        for file_path in report_files:
            if self.storage.file_exists(project_id, file_path):
                self.storage.delete_file(project_id, file_path)
                deleted_files += 1

        return RollbackResult(
            success=True,
            stage="embedding",
            message=f"Deleted {deleted_files} files",
            deleted_files=deleted_files
        )

    def _rollback_index(self, project_id: str) -> RollbackResult:
        """Delete Azure AI Search index"""
        os.environ['PRISM_PROJECT_NAME'] = project_id

        try:
            from scripts.search_index import delete_search_index
            exit_code = delete_search_index.main()

            if exit_code == 0:
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

    def _update_project_status(self, project_id: str, updates: Dict[str, Any]) -> bool:
        """Update project config status fields"""
        config = self.storage.read_json(project_id, "config.json")
        if config is None:
            return False

        if "status" not in config:
            config["status"] = {}

        config["status"].update(updates)
        return self.storage.write_json(project_id, "config.json", config)

    def get_rollback_preview(self, project_id: str, stage: str, cascade: bool = True) -> Dict[str, Any]:
        """
        Preview what would be deleted by a rollback operation.
        """
        if stage not in self.VALID_STAGES:
            return {"error": f"Invalid stage '{stage}'"}

        if not self.storage.project_exists(project_id):
            return {"error": f"Project '{project_id}' not found"}

        # Determine stages to roll back
        stages_to_rollback = [stage]
        if cascade:
            stages_to_rollback.extend(self.ROLLBACK_CASCADE.get(stage, []))
        stages_to_rollback = list(dict.fromkeys(stages_to_rollback))

        preview = {
            "stages": stages_to_rollback,
            "blob_files": {},
            "azure_resources": [],
            "warnings": []
        }

        # Check each stage
        for s in stages_to_rollback:
            if s == "extraction":
                files = self.storage.list_files(project_id, "output/extraction_results")
                if files:
                    preview["blob_files"]["extraction_results"] = len(files)

            elif s == "chunking":
                files = self.storage.list_files(project_id, "output/chunked_documents")
                if files:
                    preview["blob_files"]["chunked_documents"] = len(files)

            elif s == "embedding":
                files = self.storage.list_files(project_id, "output/embedded_documents")
                if files:
                    preview["blob_files"]["embedded_documents"] = len(files)

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
