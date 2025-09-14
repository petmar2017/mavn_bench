"""Filesystem storage adapter implementation"""

import asyncio
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import aiofiles
import aiofiles.os

from .base_storage import (
    StorageAdapter,
    StorageError,
    DocumentNotFoundError,
    VersionNotFoundError
)
from ..models.document import DocumentMessage, DocumentMetadata, DocumentVersion
from ..core.config import get_settings


class FilesystemStorage(StorageAdapter):
    """Filesystem-based storage adapter"""

    def __init__(self, base_path: Optional[str] = None):
        """Initialize filesystem storage

        Args:
            base_path: Base directory for document storage
        """
        super().__init__("filesystem")
        settings = get_settings()
        self.base_path = Path(base_path or settings.storage.filesystem_base_path)

        # Create base directory if it doesn't exist
        self.base_path.mkdir(parents=True, exist_ok=True)

        # Create subdirectories for organization
        self.documents_dir = self.base_path / "documents"
        self.versions_dir = self.base_path / "versions"
        self.metadata_dir = self.base_path / "metadata"

        for directory in [self.documents_dir, self.versions_dir, self.metadata_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Initialized filesystem storage at {self.base_path}")

    def _get_document_path(self, document_id: str) -> Path:
        """Get the file path for a document"""
        return self.documents_dir / f"{document_id}.json"

    def _get_metadata_path(self, document_id: str) -> Path:
        """Get the file path for document metadata"""
        return self.metadata_dir / f"{document_id}_metadata.json"

    def _get_version_path(self, document_id: str, version: int) -> Path:
        """Get the file path for a document version"""
        version_dir = self.versions_dir / document_id
        version_dir.mkdir(parents=True, exist_ok=True)
        return version_dir / f"v{version}.json"

    def _get_versions_index_path(self, document_id: str) -> Path:
        """Get the file path for versions index"""
        return self.versions_dir / document_id / "index.json"

    async def store(self, document_id: str, document_data: Dict[str, Any]) -> bool:
        """Store a document to filesystem (alias for compatibility)"""
        # Convert dict to DocumentMessage if needed
        if isinstance(document_data, dict):
            document = DocumentMessage(**document_data)
        else:
            document = document_data
        return await self.save(document)

    async def save(self, document: DocumentMessage) -> bool:
        """Save a document to filesystem"""
        with self.traced_operation("save", document_id=document.metadata.document_id):
            try:
                document_id = document.metadata.document_id
                document_path = self._get_document_path(document_id)
                metadata_path = self._get_metadata_path(document_id)

                # Save document data
                document_data = document.model_dump(mode="json")
                document_json = json.dumps(document_data, indent=2, default=str)

                async with aiofiles.open(document_path, 'w') as f:
                    await f.write(document_json)

                # Save metadata separately for efficient listing
                metadata_data = document.metadata.model_dump(mode="json")
                metadata_json = json.dumps(metadata_data, indent=2, default=str)

                async with aiofiles.open(metadata_path, 'w') as f:
                    await f.write(metadata_json)

                # Save initial version if it's a new document
                if document.metadata.version == 1:
                    version = DocumentVersion(
                        version=1,
                        timestamp=datetime.utcnow(),
                        user=document.metadata.created_user,
                        changes={"action": "created"},
                        commit_message="Initial version"
                    )
                    await self.save_version(document_id, version)

                self.logger.info(f"Saved document {document_id} to filesystem")
                return True

            except Exception as e:
                self.logger.error(f"Failed to save document {document_id}: {str(e)}")
                raise StorageError(f"Failed to save document: {str(e)}") from e

    async def load(self, document_id: str) -> Optional[DocumentMessage]:
        """Load a document from filesystem"""
        with self.traced_operation("load", document_id=document_id):
            try:
                document_path = self._get_document_path(document_id)

                if not await aiofiles.os.path.exists(document_path):
                    self.logger.debug(f"Document {document_id} not found")
                    return None

                async with aiofiles.open(document_path, 'r') as f:
                    document_json = await f.read()

                document_data = json.loads(document_json)
                document = DocumentMessage(**document_data)

                self.logger.info(f"Loaded document {document_id} from filesystem")
                return document

            except json.JSONDecodeError as e:
                self.logger.error(f"Invalid JSON in document {document_id}: {str(e)}")
                raise StorageError(f"Invalid document format: {str(e)}") from e
            except Exception as e:
                self.logger.error(f"Failed to load document {document_id}: {str(e)}")
                raise StorageError(f"Failed to load document: {str(e)}") from e

    async def delete(self, document_id: str) -> bool:
        """Delete a document from filesystem"""
        with self.traced_operation("delete", document_id=document_id):
            try:
                document_path = self._get_document_path(document_id)
                metadata_path = self._get_metadata_path(document_id)
                versions_dir = self.versions_dir / document_id

                deleted = False

                # Delete document file
                if await aiofiles.os.path.exists(document_path):
                    await aiofiles.os.remove(document_path)
                    deleted = True

                # Delete metadata file
                if await aiofiles.os.path.exists(metadata_path):
                    await aiofiles.os.remove(metadata_path)

                # Delete versions directory
                if await aiofiles.os.path.exists(versions_dir):
                    # Delete all version files
                    for version_file in os.listdir(versions_dir):
                        file_path = versions_dir / version_file
                        await aiofiles.os.remove(file_path)
                    # Remove the directory
                    await aiofiles.os.rmdir(versions_dir)

                if deleted:
                    self.logger.info(f"Deleted document {document_id} from filesystem")
                else:
                    self.logger.warning(f"Document {document_id} not found for deletion")

                return deleted

            except Exception as e:
                self.logger.error(f"Failed to delete document {document_id}: {str(e)}")
                raise StorageError(f"Failed to delete document: {str(e)}") from e

    async def exists(self, document_id: str) -> bool:
        """Check if a document exists"""
        with self.traced_operation("exists", document_id=document_id):
            document_path = self._get_document_path(document_id)
            exists = await aiofiles.os.path.exists(document_path)
            self.logger.debug(f"Document {document_id} exists: {exists}")
            return exists

    async def list_documents(
        self,
        user_id: Optional[str] = None,
        document_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[DocumentMetadata]:
        """List documents with optional filtering"""
        with self.traced_operation(
            "list_documents",
            user_id=user_id,
            document_type=document_type,
            limit=limit,
            offset=offset
        ):
            try:
                metadata_list = []

                # List all metadata files
                metadata_files = sorted(
                    [f for f in os.listdir(self.metadata_dir) if f.endswith("_metadata.json")]
                )

                self.logger.info(f"[FilesystemStorage] Found {len(metadata_files)} metadata files in {self.metadata_dir}")
                self.logger.info(f"[FilesystemStorage] Filter criteria - user_id: {user_id}, document_type: {document_type}")

                for metadata_file in metadata_files:
                    metadata_path = self.metadata_dir / metadata_file

                    async with aiofiles.open(metadata_path, 'r') as f:
                        metadata_json = await f.read()

                    metadata_data = json.loads(metadata_json)
                    metadata = DocumentMetadata(**metadata_data)

                    # Log each document found
                    self.logger.info(f"[FilesystemStorage] Found doc: id={metadata.document_id}, name={metadata.name}, user={metadata.created_user}, deleted={getattr(metadata, 'deleted', False)}")

                    # Apply filters
                    if user_id and metadata.created_user != user_id:
                        self.logger.info(f"[FilesystemStorage] Filtering out doc {metadata.document_id} - user mismatch: {metadata.created_user} != {user_id}")
                        continue
                    if document_type and str(metadata.document_type) != document_type:
                        continue

                    metadata_list.append(metadata)

                # Sort by updated_at descending (most recent first)
                metadata_list.sort(
                    key=lambda x: x.updated_at or x.created_at or datetime.min.isoformat(),
                    reverse=True
                )

                # Apply pagination
                start = offset
                end = offset + limit
                paginated_list = metadata_list[start:end]

                self.logger.info(
                    f"Listed {len(paginated_list)} documents "
                    f"(total: {len(metadata_list)}, offset: {offset}, limit: {limit})"
                )
                return paginated_list

            except Exception as e:
                self.logger.error(f"Failed to list documents: {str(e)}")
                raise StorageError(f"Failed to list documents: {str(e)}") from e

    async def save_version(
        self,
        document_id: str,
        version: DocumentVersion
    ) -> bool:
        """Save a document version"""
        with self.traced_operation(
            "save_version",
            document_id=document_id,
            version=version.version
        ):
            try:
                # Save version data
                version_path = self._get_version_path(document_id, version.version)
                version_data = version.model_dump(mode="json")
                version_json = json.dumps(version_data, indent=2, default=str)

                async with aiofiles.open(version_path, 'w') as f:
                    await f.write(version_json)

                # Update versions index
                index_path = self._get_versions_index_path(document_id)

                if await aiofiles.os.path.exists(index_path):
                    async with aiofiles.open(index_path, 'r') as f:
                        index_json = await f.read()
                    versions_index = json.loads(index_json)
                else:
                    versions_index = {"versions": []}

                # Add version to index if not already present
                if version.version not in [v["version"] for v in versions_index["versions"]]:
                    versions_index["versions"].append({
                        "version": version.version,
                        "timestamp": version.timestamp.isoformat(),
                        "user": version.user,
                        "commit_message": version.commit_message
                    })
                    versions_index["versions"].sort(key=lambda x: x["version"])

                index_json = json.dumps(versions_index, indent=2)
                async with aiofiles.open(index_path, 'w') as f:
                    await f.write(index_json)

                self.logger.info(f"Saved version {version.version} for document {document_id}")
                return True

            except Exception as e:
                self.logger.error(f"Failed to save version: {str(e)}")
                raise StorageError(f"Failed to save version: {str(e)}") from e

    async def get_versions(
        self,
        document_id: str
    ) -> List[DocumentVersion]:
        """Get all versions of a document"""
        with self.traced_operation("get_versions", document_id=document_id):
            try:
                index_path = self._get_versions_index_path(document_id)

                if not await aiofiles.os.path.exists(index_path):
                    self.logger.debug(f"No versions found for document {document_id}")
                    return []

                async with aiofiles.open(index_path, 'r') as f:
                    index_json = await f.read()

                versions_index = json.loads(index_json)
                versions = []

                for version_info in versions_index["versions"]:
                    version_path = self._get_version_path(document_id, version_info["version"])

                    if await aiofiles.os.path.exists(version_path):
                        async with aiofiles.open(version_path, 'r') as f:
                            version_json = await f.read()
                        version_data = json.loads(version_json)
                        versions.append(DocumentVersion(**version_data))

                self.logger.info(f"Retrieved {len(versions)} versions for document {document_id}")
                return versions

            except Exception as e:
                self.logger.error(f"Failed to get versions: {str(e)}")
                raise StorageError(f"Failed to get versions: {str(e)}") from e

    async def revert_to_version(
        self,
        document_id: str,
        version_number: int
    ) -> Optional[DocumentMessage]:
        """Revert a document to a specific version"""
        with self.traced_operation(
            "revert_to_version",
            document_id=document_id,
            version=version_number
        ):
            try:
                # Get the specific version file
                version_path = self._get_version_path(document_id, version_number)

                if not await aiofiles.os.path.exists(version_path):
                    self.logger.warning(f"Version {version_number} not found for document {document_id}")
                    raise VersionNotFoundError(f"Version {version_number} not found")

                # Load the current document
                current_doc = await self.load(document_id)
                if not current_doc:
                    raise DocumentNotFoundError(f"Document {document_id} not found")

                # For this implementation, we'll store the full document in each version
                # In a production system, you might store only diffs
                async with aiofiles.open(version_path, 'r') as f:
                    version_json = await f.read()

                version_data = json.loads(version_json)

                # Create a new version entry for the revert action
                new_version = current_doc.metadata.version + 1
                revert_version = DocumentVersion(
                    version=new_version,
                    timestamp=datetime.utcnow(),
                    user=current_doc.metadata.updated_user,
                    changes={
                        "action": "reverted",
                        "reverted_to": version_number
                    },
                    commit_message=f"Reverted to version {version_number}"
                )

                # Update document metadata
                current_doc.metadata.version = new_version
                current_doc.metadata.updated_timestamp = datetime.utcnow()
                current_doc.history.append(revert_version)

                # Save the reverted document
                await self.save(current_doc)
                await self.save_version(document_id, revert_version)

                self.logger.info(f"Reverted document {document_id} to version {version_number}")
                return current_doc

            except Exception as e:
                self.logger.error(f"Failed to revert document: {str(e)}")
                raise StorageError(f"Failed to revert document: {str(e)}") from e

    async def list_all(self) -> List[str]:
        """List all document IDs in storage

        Returns:
            List of all document IDs
        """
        with self.traced_operation("list_all"):
            try:
                # Get all metadata files
                metadata_files = [
                    f for f in os.listdir(self.metadata_dir)
                    if f.endswith("_metadata.json")
                ]

                # Extract document IDs from filenames
                document_ids = []
                for filename in metadata_files:
                    # Remove "_metadata.json" suffix to get document ID
                    doc_id = filename.replace("_metadata.json", "")
                    document_ids.append(doc_id)

                self.logger.info(f"Found {len(document_ids)} documents in storage")
                return document_ids

            except Exception as e:
                self.logger.error(f"Failed to list documents: {str(e)}")
                raise StorageError(f"Failed to list documents: {str(e)}") from e

    async def health_check(self) -> Dict[str, Any]:
        """Check filesystem storage health"""
        with self.traced_operation("health_check"):
            try:
                # Check if base directories exist and are writable
                checks = {
                    "base_path_exists": self.base_path.exists(),
                    "base_path_writable": os.access(self.base_path, os.W_OK),
                    "documents_dir_exists": self.documents_dir.exists(),
                    "versions_dir_exists": self.versions_dir.exists(),
                    "metadata_dir_exists": self.metadata_dir.exists(),
                }

                # Count documents
                document_count = len(
                    [f for f in os.listdir(self.documents_dir) if f.endswith(".json")]
                )

                # Check disk space (simple check)
                stat = os.statvfs(self.base_path)
                free_space_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)

                health_status = {
                    "status": "healthy" if all(checks.values()) else "unhealthy",
                    "storage_type": self.storage_type,
                    "base_path": str(self.base_path),
                    "checks": checks,
                    "document_count": document_count,
                    "free_space_gb": round(free_space_gb, 2)
                }

                self.logger.info(f"Health check: {health_status['status']}")
                return health_status

            except Exception as e:
                self.logger.error(f"Health check failed: {str(e)}")
                return {
                    "status": "error",
                    "storage_type": self.storage_type,
                    "error": str(e)
                }