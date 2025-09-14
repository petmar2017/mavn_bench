"""Base storage adapter interface for Mavn Bench"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import json
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from ..models.document import DocumentMessage, DocumentMetadata, DocumentVersion
from ..core.logger import CentralizedLogger
from ..core.telemetry import get_tracer


class StorageAdapter(ABC):
    """Abstract base class for storage adapters"""

    def __init__(self, storage_type: str):
        """Initialize storage adapter

        Args:
            storage_type: Type identifier for the storage backend
        """
        self.storage_type = storage_type
        self.logger = CentralizedLogger(f"Storage-{storage_type}")
        self.tracer = get_tracer(f"storage.{storage_type}")

    @abstractmethod
    async def save(self, document: DocumentMessage) -> bool:
        """Save a document to storage

        Args:
            document: Document to save

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def load(self, document_id: str) -> Optional[DocumentMessage]:
        """Load a document from storage

        Args:
            document_id: ID of the document to load

        Returns:
            Document if found, None otherwise
        """
        pass

    @abstractmethod
    async def delete(self, document_id: str) -> bool:
        """Delete a document from storage

        Args:
            document_id: ID of the document to delete

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def exists(self, document_id: str) -> bool:
        """Check if a document exists

        Args:
            document_id: ID of the document to check

        Returns:
            True if document exists, False otherwise
        """
        pass

    @abstractmethod
    async def list_all(self) -> List[str]:
        """List all document IDs in storage

        Returns:
            List of all document IDs
        """
        pass

    @abstractmethod
    async def list_documents(
        self,
        user_id: Optional[str] = None,
        document_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[DocumentMetadata]:
        """List documents with optional filtering

        Args:
            user_id: Filter by user ID
            document_type: Filter by document type
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of document metadata
        """
        pass

    @abstractmethod
    async def save_version(
        self,
        document_id: str,
        version: DocumentVersion
    ) -> bool:
        """Save a document version

        Args:
            document_id: ID of the document
            version: Version information to save

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def get_versions(
        self,
        document_id: str
    ) -> List[DocumentVersion]:
        """Get all versions of a document

        Args:
            document_id: ID of the document

        Returns:
            List of document versions
        """
        pass

    @abstractmethod
    async def revert_to_version(
        self,
        document_id: str,
        version_number: int
    ) -> Optional[DocumentMessage]:
        """Revert a document to a specific version

        Args:
            document_id: ID of the document
            version_number: Version to revert to

        Returns:
            Document at specified version if successful, None otherwise
        """
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check storage health status

        Returns:
            Health status dictionary
        """
        pass

    @contextmanager
    def traced_operation(self, operation_name: str, **attributes):
        """Create a traced operation context with automatic logging

        Args:
            operation_name: Name of the operation
            **attributes: Additional span attributes

        Returns:
            Trace context manager
        """
        with self.tracer.start_as_current_span(
            f"storage.{self.storage_type}.{operation_name}",
            attributes=attributes
        ) as span:
            try:
                # Log operation start with trace context
                self.logger.debug(
                    f"Starting {operation_name} operation",
                    extra={"attributes": attributes}
                )
                yield span
                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                # Log error with trace context
                self.logger.error(
                    f"Error in {operation_name} operation: {str(e)}",
                    exc_info=True
                )
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise


class StorageError(Exception):
    """Base exception for storage operations"""
    pass


class DocumentNotFoundError(StorageError):
    """Exception raised when document is not found"""
    pass


class StorageConnectionError(StorageError):
    """Exception raised when storage connection fails"""
    pass


class VersionNotFoundError(StorageError):
    """Exception raised when document version is not found"""
    pass