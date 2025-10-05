"""Document service for CRUD operations and document management"""

import asyncio
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime

from .base_service import BaseService
from .service_factory import ServiceFactory, ServiceType
from ..models.document import (
    DocumentMessage,
    DocumentMetadata,
    DocumentContent,
    DocumentVersion,
    AuditLogEntry,
    DocumentAction
)
from ..storage.base_storage import StorageAdapter, DocumentNotFoundError
from ..storage.storage_factory import StorageFactory


class DocumentService(BaseService):
    """Service for document CRUD operations and management"""

    def __init__(self, storage: Optional[StorageAdapter] = None):
        """Initialize document service

        Args:
            storage: Storage adapter to use (will use default if not provided)
        """
        super().__init__("DocumentService")
        self.storage = storage or StorageFactory.get_default()
        self.logger.info("Initialized DocumentService")

    async def create_document(
        self,
        document: DocumentMessage,
        user_id: str
    ) -> DocumentMessage:
        """Create a new document

        Args:
            document: Document to create
            user_id: ID of the user creating the document

        Returns:
            Created document with metadata

        Raises:
            ValueError: If document already exists
        """
        with self.traced_operation(
            "create_document",
            document_id=document.metadata.document_id,
            user_id=user_id
        ):
            try:
                # Check if document already exists
                if await self.storage.exists(document.metadata.document_id):
                    raise ValueError(f"Document {document.metadata.document_id} already exists")

                # Set creation metadata
                document.metadata.created_user = user_id
                document.metadata.updated_user = user_id
                document.metadata.created_timestamp = datetime.utcnow()
                document.metadata.updated_timestamp = datetime.utcnow()
                document.metadata.version = 1

                # Add audit log entry
                audit_entry = AuditLogEntry(
                    timestamp=datetime.utcnow(),
                    user=user_id,
                    action="created",
                    details={"document_id": document.metadata.document_id}
                )
                document.audit_log.append(audit_entry)

                # Save document
                success = await self.storage.save(document)
                if not success:
                    raise RuntimeError("Failed to save document")

                self.logger.info(f"Created document: {document.metadata.document_id}")
                return document

            except Exception as e:
                self.logger.error(f"Failed to create document: {str(e)}")
                raise

    async def get_document(
        self,
        document_id: str,
        user_id: Optional[str] = None
    ) -> Optional[DocumentMessage]:
        """Get a document by ID

        Args:
            document_id: ID of the document to retrieve
            user_id: ID of the user requesting the document (for access control)

        Returns:
            Document if found and accessible, None otherwise
        """
        with self.traced_operation(
            "get_document",
            document_id=document_id,
            user_id=user_id
        ):
            try:
                document = await self.storage.load(document_id)

                if document:
                    # Add audit log entry for access
                    if user_id:
                        audit_entry = AuditLogEntry(
                            timestamp=datetime.utcnow(),
                            user=user_id,
                            action="accessed",
                            details={"document_id": document_id}
                        )
                        document.audit_log.append(audit_entry)

                    self.logger.info(f"Retrieved document: {document_id}")
                else:
                    self.logger.warning(f"Document not found: {document_id}")

                return document

            except Exception as e:
                self.logger.error(f"Failed to get document {document_id}: {str(e)}")
                raise

    async def update_document(
        self,
        document_id: str,
        updates: Dict[str, Any],
        user_id: str
    ) -> Optional[DocumentMessage]:
        """Update an existing document

        Args:
            document_id: ID of the document to update
            updates: Dictionary of updates to apply
            user_id: ID of the user updating the document

        Returns:
            Updated document if successful, None if document not found

        Raises:
            ValueError: If updates are invalid
        """
        with self.traced_operation(
            "update_document",
            document_id=document_id,
            user_id=user_id,
            update_keys=list(updates.keys())
        ):
            try:
                # Load existing document
                document = await self.storage.load(document_id)
                if not document:
                    self.logger.warning(f"Document not found for update: {document_id}")
                    return None

                # Save current version
                current_version = DocumentVersion(
                    version=document.metadata.version,
                    timestamp=document.metadata.updated_timestamp,
                    user=document.metadata.updated_user,
                    changes={"snapshot": "before_update"},
                    commit_message=f"Snapshot before update by {user_id}"
                )
                await self.storage.save_version(document_id, current_version)

                # Apply updates
                for key, value in updates.items():
                    if key in ["content", "metadata"]:
                        # Handle nested updates
                        if key == "content" and isinstance(value, dict):
                            for content_key, content_value in value.items():
                                if hasattr(document.content, content_key):
                                    setattr(document.content, content_key, content_value)
                        elif key == "metadata" and isinstance(value, dict):
                            for meta_key, meta_value in value.items():
                                if hasattr(document.metadata, meta_key):
                                    setattr(document.metadata, meta_key, meta_value)
                    elif hasattr(document, key):
                        setattr(document, key, value)

                # Update metadata
                document.metadata.version += 1
                document.metadata.updated_user = user_id
                document.metadata.updated_timestamp = datetime.utcnow()

                # Add audit log entry
                audit_entry = AuditLogEntry(
                    timestamp=datetime.utcnow(),
                    user=user_id,
                    action="updated",
                    details={
                        "document_id": document_id,
                        "version": document.metadata.version,
                        "changes": list(updates.keys())
                    }
                )
                document.audit_log.append(audit_entry)

                # Save updated document
                success = await self.storage.save(document)
                if not success:
                    raise RuntimeError("Failed to save updated document")

                # Save new version
                new_version = DocumentVersion(
                    version=document.metadata.version,
                    timestamp=document.metadata.updated_timestamp,
                    user=user_id,
                    changes=updates,
                    commit_message=f"Updated by {user_id}"
                )
                await self.storage.save_version(document_id, new_version)

                self.logger.info(f"Updated document: {document_id} to version {document.metadata.version}")
                return document

            except Exception as e:
                self.logger.error(f"Failed to update document {document_id}: {str(e)}")
                raise

    async def delete_document(
        self,
        document_id: str,
        user_id: str,
        soft_delete: bool = True
    ) -> bool:
        """Delete a document

        Args:
            document_id: ID of the document to delete
            user_id: ID of the user deleting the document
            soft_delete: If True, mark as deleted but keep data; if False, permanently delete

        Returns:
            True if successful, False otherwise
        """
        with self.traced_operation(
            "delete_document",
            document_id=document_id,
            user_id=user_id,
            soft_delete=soft_delete
        ):
            try:
                if soft_delete:
                    # Soft delete: mark as deleted but keep data
                    document = await self.storage.load(document_id)
                    if not document:
                        self.logger.warning(f"Document not found for deletion: {document_id}")
                        return False

                    # Update metadata to mark as deleted
                    updates = {
                        "metadata": {
                            "deleted": True,
                            "deleted_by": user_id,
                            "deleted_at": datetime.utcnow().isoformat()
                        }
                    }

                    updated = await self.update_document(document_id, updates, user_id)
                    success = updated is not None
                else:
                    # Hard delete: permanently remove document
                    success = await self.storage.delete(document_id)

                    if success:
                        # Log the deletion (would normally go to a separate audit log)
                        self.logger.info(f"Permanently deleted document: {document_id} by user {user_id}")

                return success

            except Exception as e:
                self.logger.error(f"Failed to delete document {document_id}: {str(e)}")
                raise

    async def list_documents(
        self,
        user_id: Optional[str] = None,
        document_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        include_deleted: bool = False
    ) -> List[DocumentMessage]:
        """List documents with optional filtering

        Args:
            user_id: Filter by user ID
            document_type: Filter by document type
            limit: Maximum number of results
            offset: Number of results to skip
            include_deleted: Whether to include soft-deleted documents

        Returns:
            List of document messages
        """
        with self.traced_operation(
            "list_documents",
            user_id=user_id,
            document_type=document_type,
            limit=limit,
            offset=offset
        ):
            try:
                # Get documents from storage
                self.logger.info(f"[DocumentService] list_documents called - user_id: {user_id}, type: {document_type}, limit: {limit}, offset: {offset}, include_deleted: {include_deleted}")

                documents = await self.storage.list_documents(
                    user_id=user_id,
                    document_type=document_type,
                    limit=limit,
                    offset=offset
                )

                self.logger.info(f"[DocumentService] Retrieved {len(documents)} documents from storage")

                # Filter out deleted documents if requested
                if not include_deleted:
                    original_count = len(documents)
                    documents = [
                        doc for doc in documents
                        if not getattr(doc.metadata, "deleted", False)
                    ]
                    self.logger.info(f"[DocumentService] After filtering deleted: {original_count} -> {len(documents)} documents")

                self.logger.info(f"[DocumentService] Returning {len(documents)} documents")
                return documents

            except Exception as e:
                self.logger.error(f"Failed to list documents: {str(e)}")
                raise

    async def get_document_versions(
        self,
        document_id: str,
        user_id: Optional[str] = None
    ) -> List[DocumentVersion]:
        """Get all versions of a document

        Args:
            document_id: ID of the document
            user_id: ID of the user requesting versions (for access control)

        Returns:
            List of document versions
        """
        with self.traced_operation(
            "get_document_versions",
            document_id=document_id,
            user_id=user_id
        ):
            try:
                versions = await self.storage.get_versions(document_id)

                if versions and user_id:
                    # Log access to versions
                    self.logger.info(f"User {user_id} accessed versions of document {document_id}")

                return versions

            except Exception as e:
                self.logger.error(f"Failed to get versions for {document_id}: {str(e)}")
                raise

    async def revert_document(
        self,
        document_id: str,
        version_number: int,
        user_id: str
    ) -> Optional[DocumentMessage]:
        """Revert a document to a specific version

        Args:
            document_id: ID of the document
            version_number: Version to revert to
            user_id: ID of the user performing the revert

        Returns:
            Reverted document if successful, None otherwise
        """
        with self.traced_operation(
            "revert_document",
            document_id=document_id,
            version_number=version_number,
            user_id=user_id
        ):
            try:
                # Revert using storage
                document = await self.storage.revert_to_version(document_id, version_number)

                if document:
                    # Add audit log entry
                    audit_entry = AuditLogEntry(
                        timestamp=datetime.utcnow(),
                        user=user_id,
                        action="reverted",
                        details={
                            "document_id": document_id,
                            "reverted_to_version": version_number,
                            "new_version": document.metadata.version
                        }
                    )
                    document.audit_log.append(audit_entry)

                    # Save with audit log
                    await self.storage.save(document)

                    self.logger.info(f"Reverted document {document_id} to version {version_number}")

                return document

            except Exception as e:
                self.logger.error(f"Failed to revert document {document_id}: {str(e)}")
                raise

    async def search_documents(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 10
    ) -> List[DocumentMessage]:
        """Search for documents (basic implementation, will be enhanced with search services)

        Args:
            query: Search query
            user_id: ID of the user searching
            limit: Maximum number of results

        Returns:
            List of matching document messages
        """
        with self.traced_operation(
            "search_documents",
            query=query,
            user_id=user_id,
            limit=limit
        ):
            try:
                # For now, just filter by name containing query
                # This will be replaced with proper search services later
                all_docs = await self.list_documents(user_id=user_id, limit=1000)

                matching = [
                    doc for doc in all_docs
                    if query.lower() in doc.metadata.name.lower() or
                    (doc.metadata.summary and query.lower() in doc.metadata.summary.lower())
                ]

                # Limit results
                matching = matching[:limit]

                self.logger.info(f"Found {len(matching)} documents matching '{query}'")
                return matching

            except Exception as e:
                self.logger.error(f"Failed to search documents: {str(e)}")
                raise

    async def health_check(self) -> Dict[str, Any]:
        """Check service health

        Returns:
            Health status dictionary
        """
        with self.traced_operation("health_check"):
            try:
                # Check storage health
                storage_health = await self.storage.health_check()

                # Count documents
                try:
                    docs = await self.storage.list_documents(limit=1)
                    doc_count = len(docs)
                    list_status = "healthy"
                except Exception as e:
                    doc_count = 0
                    list_status = f"error: {str(e)}"

                health_status = {
                    "service": "DocumentService",
                    "status": "healthy" if storage_health.get("status") == "healthy" else "degraded",
                    "storage": storage_health,
                    "operations": {
                        "list_documents": list_status,
                        "document_count": doc_count
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }

                self.logger.info(f"Health check: {health_status['status']}")
                return health_status

            except Exception as e:
                self.logger.error(f"Health check failed: {str(e)}")
                return {
                    "service": "DocumentService",
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }


# Register with factory
ServiceFactory.register(ServiceType.DOCUMENT, DocumentService)