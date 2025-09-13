"""Tests for DocumentService"""

import pytest
from datetime import datetime
from typing import List

from src.services.document_service import DocumentService
from src.models.document import (
    DocumentMessage,
    DocumentMetadata,
    DocumentContent,
    DocumentType,
    DocumentVersion,
    AuditLogEntry
)
from src.storage.filesystem_storage import FilesystemStorage


class TestDocumentService:
    """Test suite for DocumentService"""

    @pytest.fixture
    def storage(self, temp_dir):
        """Create a storage instance for testing"""
        return FilesystemStorage(base_path=str(temp_dir))

    @pytest.fixture
    def service(self, storage):
        """Create a DocumentService instance for testing"""
        return DocumentService(storage=storage)

    @pytest.fixture
    def test_document(self) -> DocumentMessage:
        """Create a test document"""
        metadata = DocumentMetadata(
            document_id="test-doc-001",
            document_type=DocumentType.MARKDOWN,
            name="Test Document",
            summary="A test document",
            created_user="test_user",
            updated_user="test_user",
            version=1
        )

        content = DocumentContent(
            formatted_content="# Test Document\n\nThis is test content.",
            raw_text="Test Document. This is test content."
        )

        return DocumentMessage(
            metadata=metadata,
            content=content,
            user_id="test_user"
        )

    @pytest.mark.asyncio
    async def test_create_document(self, service, test_document):
        """Test creating a new document"""
        # Create document
        created_doc = await service.create_document(test_document, "test_user")

        assert created_doc is not None
        assert created_doc.metadata.document_id == test_document.metadata.document_id
        assert created_doc.metadata.created_user == "test_user"
        assert created_doc.metadata.version == 1
        assert len(created_doc.audit_log) > 0
        assert created_doc.audit_log[0].action == "created"

    @pytest.mark.asyncio
    async def test_create_duplicate_document(self, service, test_document):
        """Test that creating duplicate document raises error"""
        # Create first document
        await service.create_document(test_document, "test_user")

        # Try to create duplicate
        with pytest.raises(ValueError, match="already exists"):
            await service.create_document(test_document, "test_user")

    @pytest.mark.asyncio
    async def test_get_document(self, service, test_document):
        """Test retrieving a document"""
        # Create document first
        await service.create_document(test_document, "test_user")

        # Get document
        retrieved = await service.get_document(
            test_document.metadata.document_id,
            "test_user"
        )

        assert retrieved is not None
        assert retrieved.metadata.document_id == test_document.metadata.document_id
        assert retrieved.metadata.name == test_document.metadata.name

    @pytest.mark.asyncio
    async def test_get_nonexistent_document(self, service):
        """Test retrieving a document that doesn't exist"""
        retrieved = await service.get_document("nonexistent-id", "test_user")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_update_document(self, service, test_document):
        """Test updating a document"""
        # Create document
        await service.create_document(test_document, "test_user")

        # Update document
        updates = {
            "metadata": {
                "name": "Updated Document Name",
                "summary": "Updated summary"
            }
        }

        updated = await service.update_document(
            test_document.metadata.document_id,
            updates,
            "test_user"
        )

        assert updated is not None
        assert updated.metadata.name == "Updated Document Name"
        assert updated.metadata.summary == "Updated summary"
        assert updated.metadata.version == 2
        assert updated.metadata.updated_user == "test_user"

    @pytest.mark.asyncio
    async def test_update_nonexistent_document(self, service):
        """Test updating a document that doesn't exist"""
        updates = {"metadata": {"name": "New Name"}}
        updated = await service.update_document("nonexistent-id", updates, "test_user")
        assert updated is None

    @pytest.mark.asyncio
    async def test_delete_document_soft(self, service, test_document):
        """Test soft deleting a document"""
        # Create document
        await service.create_document(test_document, "test_user")

        # Soft delete
        success = await service.delete_document(
            test_document.metadata.document_id,
            "test_user",
            soft_delete=True
        )

        assert success is True

        # Document should still exist but be marked as deleted
        retrieved = await service.get_document(test_document.metadata.document_id)
        assert retrieved is not None

    @pytest.mark.asyncio
    async def test_delete_document_hard(self, service, test_document):
        """Test hard deleting a document"""
        # Create document
        await service.create_document(test_document, "test_user")

        # Hard delete
        success = await service.delete_document(
            test_document.metadata.document_id,
            "test_user",
            soft_delete=False
        )

        assert success is True

        # Document should not exist
        retrieved = await service.get_document(test_document.metadata.document_id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_document(self, service):
        """Test deleting a document that doesn't exist"""
        success = await service.delete_document("nonexistent-id", "test_user")
        assert success is False

    @pytest.mark.asyncio
    async def test_list_documents(self, service, test_document, another_document):
        """Test listing documents"""
        # Create multiple documents
        await service.create_document(test_document, "test_user")
        await service.create_document(another_document, "another_user")

        # List all documents
        docs = await service.list_documents()
        assert len(docs) == 2

        # List by user
        user_docs = await service.list_documents(user_id="test_user")
        assert len(user_docs) == 1
        assert user_docs[0].document_id == test_document.metadata.document_id

        # List with pagination
        paginated = await service.list_documents(limit=1, offset=0)
        assert len(paginated) == 1

    @pytest.mark.asyncio
    async def test_get_document_versions(self, service, test_document):
        """Test getting document versions"""
        # Create document
        await service.create_document(test_document, "test_user")

        # Make some updates to create versions
        for i in range(2, 4):
            updates = {"metadata": {"summary": f"Version {i}"}}
            await service.update_document(
                test_document.metadata.document_id,
                updates,
                "test_user"
            )

        # Get versions
        versions = await service.get_document_versions(
            test_document.metadata.document_id,
            "test_user"
        )

        assert len(versions) >= 2  # At least the versions we created

    @pytest.mark.asyncio
    async def test_revert_document(self, service, test_document):
        """Test reverting a document to a previous version"""
        # Create document
        await service.create_document(test_document, "test_user")

        # Update document
        updates = {"metadata": {"summary": "Updated summary"}}
        await service.update_document(
            test_document.metadata.document_id,
            updates,
            "test_user"
        )

        # Revert to version 1
        reverted = await service.revert_document(
            test_document.metadata.document_id,
            1,
            "test_user"
        )

        assert reverted is not None
        assert reverted.metadata.version > 2  # Should be a new version
        assert any("reverted" in entry.action for entry in reverted.audit_log)

    @pytest.mark.asyncio
    async def test_search_documents(self, service, test_document):
        """Test searching for documents"""
        # Create document with searchable content
        test_document.metadata.name = "Important Research Paper"
        test_document.metadata.summary = "A paper about machine learning"
        await service.create_document(test_document, "test_user")

        # Search by name
        results = await service.search_documents("Research", "test_user")
        assert len(results) == 1
        assert results[0].document_id == test_document.metadata.document_id

        # Search by summary
        results = await service.search_documents("machine learning", "test_user")
        assert len(results) == 1

        # Search with no matches
        results = await service.search_documents("nonexistent", "test_user")
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_health_check(self, service):
        """Test service health check"""
        health = await service.health_check()

        assert health["service"] == "DocumentService"
        assert health["status"] in ["healthy", "degraded", "error"]
        assert "storage" in health
        assert "operations" in health
        assert "timestamp" in health

    @pytest.mark.asyncio
    async def test_audit_logging(self, service, test_document):
        """Test that all operations are properly audit logged"""
        # Create document
        created = await service.create_document(test_document, "user1")
        assert len(created.audit_log) == 1
        assert created.audit_log[0].action == "created"
        assert created.audit_log[0].user == "user1"

        # Access document
        accessed = await service.get_document(
            test_document.metadata.document_id,
            "user2"
        )
        assert len(accessed.audit_log) == 2
        assert accessed.audit_log[1].action == "accessed"
        assert accessed.audit_log[1].user == "user2"

        # Update document
        updates = {"metadata": {"name": "Updated Name"}}
        updated = await service.update_document(
            test_document.metadata.document_id,
            updates,
            "user3"
        )
        assert any(entry.action == "updated" and entry.user == "user3"
                  for entry in updated.audit_log)