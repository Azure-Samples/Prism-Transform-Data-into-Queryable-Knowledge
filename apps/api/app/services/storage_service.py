"""
Azure Blob Storage Service for Prism

Authentication:
- Local Docker: Azurite emulator (connection string)
- Container Apps: System-assigned Managed Identity (DefaultAzureCredential)

All project data stored in Azure Blob Storage:
    {container}/
        {project_name}/
            documents/
            output/
                extraction_results/
                chunked_documents/
                embedded_documents/
                results.json
            config.json
            workflow_config.json
"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError, HttpResponseError

from scripts.logging_config import get_logger

logger = get_logger(__name__)


class StorageService:
    """Azure Blob Storage service."""

    def __init__(self):
        self.container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "prism-projects")

        # Check for connection string (Azurite / local dev)
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "").strip()

        if connection_string:
            # Local development with Azurite
            self.account_name = "devstoreaccount1"
            logger.info("Using Azurite (connection string)")
            self._blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        else:
            # Azure with DefaultAzureCredential (Managed Identity)
            self.account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
            if not self.account_name:
                raise ValueError("AZURE_STORAGE_ACCOUNT_NAME or AZURE_STORAGE_CONNECTION_STRING must be set")

            account_url = f"https://{self.account_name}.blob.core.windows.net"
            logger.info("Using DefaultAzureCredential (Managed Identity)")
            credential = DefaultAzureCredential()
            self._blob_service_client = BlobServiceClient(account_url, credential=credential)

        self._container_client = self._blob_service_client.get_container_client(self.container_name)

        # Ensure container exists (skip creation if using managed identity - container created by Bicep)
        try:
            self._container_client.create_container()
            logger.info(f"Created blob container: {self.container_name}")
        except ResourceExistsError:
            pass
        except HttpResponseError as e:
            # With RBAC/managed identity, create_container may fail even with correct permissions
            # The container is created by Bicep, so we just verify it exists
            if "AuthorizationFailure" in str(e) or "AuthenticationFailed" in str(e):
                logger.info(f"Container creation skipped (RBAC mode), verifying container exists...")
                if not self._container_client.exists():
                    raise ValueError(f"Container {self.container_name} does not exist and cannot be created")
                logger.info(f"Container {self.container_name} exists")
            else:
                raise

        logger.info(f"Storage initialized: {self.account_name}/{self.container_name}")

    def list_projects(self) -> List[str]:
        """List all project names."""
        projects = set()
        blobs = self._container_client.list_blobs()
        for blob in blobs:
            parts = blob.name.split('/')
            if parts and parts[0] and not parts[0].startswith('.'):
                projects.add(parts[0])
        return sorted(list(projects))

    def project_exists(self, project_name: str) -> bool:
        """Check if a project exists."""
        blob_client = self._container_client.get_blob_client(f"{project_name}/config.json")
        return blob_client.exists()

    def create_project(self, project_name: str) -> bool:
        """Create a new project."""
        try:
            config = {
                "name": project_name,
                "description": "",
                "created_at": datetime.utcnow().isoformat() + "Z",
                "status": {}
            }
            self.write_json(project_name, "config.json", config)
            self.write_json(project_name, "workflow_config.json", {"sections": []})
            return True
        except Exception as e:
            logger.error(f"Failed to create project: {e}")
            return False

    def delete_project(self, project_name: str) -> bool:
        """Delete a project and all its contents."""
        try:
            blobs = self._container_client.list_blobs(name_starts_with=f"{project_name}/")
            for blob in blobs:
                self._container_client.delete_blob(blob.name)
            return True
        except Exception as e:
            logger.error(f"Failed to delete project: {e}")
            return False

    def read_file(self, project_name: str, relative_path: str) -> Optional[bytes]:
        """Read a file."""
        try:
            blob_client = self._container_client.get_blob_client(f"{project_name}/{relative_path}")
            return blob_client.download_blob().readall()
        except ResourceNotFoundError:
            return None
        except Exception as e:
            logger.error(f"Failed to read {relative_path}: {e}")
            return None

    def write_file(self, project_name: str, relative_path: str, content: bytes) -> bool:
        """Write a file."""
        try:
            blob_client = self._container_client.get_blob_client(f"{project_name}/{relative_path}")
            blob_client.upload_blob(content, overwrite=True)
            return True
        except Exception as e:
            logger.error(f"Failed to write {relative_path}: {e}")
            return False

    def delete_file(self, project_name: str, relative_path: str) -> bool:
        """Delete a file."""
        try:
            self._container_client.delete_blob(f"{project_name}/{relative_path}")
            return True
        except ResourceNotFoundError:
            return False
        except Exception as e:
            logger.error(f"Failed to delete {relative_path}: {e}")
            return False

    def file_exists(self, project_name: str, relative_path: str) -> bool:
        """Check if a file exists."""
        blob_client = self._container_client.get_blob_client(f"{project_name}/{relative_path}")
        return blob_client.exists()

    def list_files(self, project_name: str, prefix: str = "", recursive: bool = True) -> List[Dict[str, Any]]:
        """
        List files in a directory.

        Args:
            project_name: Project name
            prefix: Directory prefix (e.g., "output/extraction_results")
            recursive: If True, include files in subdirectories

        Returns:
            List of file info dicts with 'name', 'path' (project-relative), 'size', 'modified'
        """
        files = []
        # Build blob prefix
        if prefix:
            # Remove trailing slash if present, we'll add it
            prefix = prefix.rstrip('/')
            blob_prefix = f"{project_name}/{prefix}/"
        else:
            blob_prefix = f"{project_name}/"

        project_prefix = f"{project_name}/"
        blobs = self._container_client.list_blobs(name_starts_with=blob_prefix)

        for blob in blobs:
            if blob.name.endswith('.placeholder'):
                continue

            # Get path relative to project (not to prefix)
            project_relative_path = blob.name[len(project_prefix):]
            if not project_relative_path or project_relative_path.endswith('/'):
                continue

            # Get path relative to the prefix for subdirectory check
            prefix_relative_path = blob.name[len(blob_prefix):]

            # Skip subdirectories if not recursive
            if not recursive and '/' in prefix_relative_path:
                continue

            filename = os.path.basename(project_relative_path)
            if filename.startswith('.'):
                continue

            files.append({
                "name": filename,
                "path": project_relative_path,  # Full path relative to project
                "size": blob.size,
                "modified": blob.last_modified.isoformat() if blob.last_modified else None
            })

        return sorted(files, key=lambda f: f["name"])

    def read_json(self, project_name: str, relative_path: str) -> Optional[Dict]:
        """Read JSON file."""
        content = self.read_file(project_name, relative_path)
        if content is None:
            return None
        try:
            return json.loads(content.decode('utf-8'))
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON {relative_path}: {e}")
            return None

    def write_json(self, project_name: str, relative_path: str, data: Dict) -> bool:
        """Write JSON file."""
        content = json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8')
        return self.write_file(project_name, relative_path, content)


# Singleton
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Get storage service singleton."""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
