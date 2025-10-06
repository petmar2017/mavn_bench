"""Tests for FilesystemStorage adapter"""

import pytest
import json
from pathlib import Path
from datetime import datetime

from src.storage.filesystem_storage import FilesystemStorage
from src.storage.base_storage import DocumentNotFoundError, VersionNotFoundError
from src.models.document import DocumentMessage, DocumentVersion


class TestFilesystemStorage:
    """Test suite for FilesystemStorage"""

    @pytest.fixture
    def storage(self, temp_dir):
        """Create a FilesystemStorage instance for testing"""
        return FilesystemStorage(base_path=str(temp_dir))

    @pytest.mark.asyncio
    async def test_initialization(self, temp_dir):
        """Test storage initialization creates required directories"""
        storage = FilesystemStorage(base_path=str(temp_dir))

        # Check that directories were created
        assert (temp_dir / "documents").exists()
        assert (temp_dir / "versions").exists()
        assert (temp_dir / "metadata").exists()

    @pytest.mark.asyncio
    async def test_save_document(self, storage, sample_document, temp_dir):
        """Test saving a document to filesystem"""
        result = await storage.save(sample_document)

        assert result is True

        # Check files were created
        doc_path = temp_dir / "documents" / f"{sample_document.metadata.document_id}.json"
        metadata_path = temp_dir / "metadata" / f"{sample_document.metadata.document_id}_metadata.json"

        assert doc_path.exists()
        assert metadata_path.exists()

        # Verify content
        with open(doc_path) as f:
            saved_data = json.load(f)
            assert saved_data["metadata"]["document_id"] == sample_document.metadata.document_id
            assert saved_data["metadata"]["name"] == sample_document.metadata.name

    @pytest.mark.asyncio
    async def test_load_document(self, storage, sample_document):
        """Test loading a document from filesystem"""
        # Save first
        await storage.save(sample_document)

        # Load document
        loaded_doc = await storage.load(sample_document.metadata.document_id)

        assert loaded_doc is not None
        assert loaded_doc.metadata.document_id == sample_document.metadata.document_id
        assert loaded_doc.metadata.name == sample_document.metadata.name
        assert loaded_doc.content.formatted_content == sample_document.content.formatted_content

    @pytest.mark.asyncio
    async def test_load_nonexistent_document(self, storage):
        """Test loading a document that doesn't exist"""
        loaded_doc = await storage.load("nonexistent-id")
        assert loaded_doc is None

    @pytest.mark.asyncio
    async def test_delete_document(self, storage, sample_document):
        """Test deleting a document"""
        # Save first
        await storage.save(sample_document)

        # Verify it exists
        assert await storage.exists(sample_document.metadata.document_id)

        # Delete
        result = await storage.delete(sample_document.metadata.document_id)
        assert result is True

        # Verify it's gone
        assert not await storage.exists(sample_document.metadata.document_id)
        loaded = await storage.load(sample_document.metadata.document_id)
        assert loaded is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_document(self, storage):
        """Test deleting a document that doesn't exist"""
        result = await storage.delete("nonexistent-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_exists(self, storage, sample_document):
        """Test checking document existence"""
        # Should not exist initially
        assert not await storage.exists(sample_document.metadata.document_id)

        # Save document
        await storage.save(sample_document)

        # Should exist now
        assert await storage.exists(sample_document.metadata.document_id)

    @pytest.mark.asyncio
    async def test_list_documents(self, storage, sample_document, another_document):
        """Test listing documents with filtering"""
        # Save multiple documents
        await storage.save(sample_document)
        await storage.save(another_document)

        # List all documents
        all_docs = await storage.list_documents()
        assert len(all_docs) == 2

        # Filter by user
        user_docs = await storage.list_documents(user_id="test_user")
        assert len(user_docs) == 1
        assert user_docs[0].document_id == sample_document.metadata.document_id

        # Filter by document type
        pdf_docs = await storage.list_documents(document_type=str(sample_document.metadata.document_type))
        assert len(pdf_docs) == 1
        assert pdf_docs[0].document_type == sample_document.metadata.document_type

        # Test pagination
        paginated = await storage.list_documents(limit=1, offset=0)
        assert len(paginated) == 1

        paginated_offset = await storage.list_documents(limit=1, offset=1)
        assert len(paginated_offset) == 1
        assert paginated[0].document_id != paginated_offset[0].document_id

    @pytest.mark.asyncio
    async def test_save_version(self, storage, sample_document):
        """Test saving document versions"""
        # Save document first
        await storage.save(sample_document)

        # Create and save a new version
        version = DocumentVersion(
            version=2,
            timestamp=datetime.utcnow(),
            user="test_user",
            changes={"content": "updated"},
            commit_message="Updated content"
        )

        result = await storage.save_version(sample_document.metadata.document_id, version)
        assert result is True

        # Verify version was saved
        versions = await storage.get_versions(sample_document.metadata.document_id)
        assert len(versions) >= 1  # At least the version we just saved

    @pytest.mark.asyncio
    async def test_get_versions(self, storage, sample_document):
        """Test retrieving document versions"""
        # Save document
        await storage.save(sample_document)

        # Save multiple versions
        for i in range(2, 5):
            version = DocumentVersion(
                version=i,
                timestamp=datetime.utcnow(),
                user="test_user",
                changes={"version": i},
                commit_message=f"Version {i}"
            )
            await storage.save_version(sample_document.metadata.document_id, version)

        # Get all versions
        versions = await storage.get_versions(sample_document.metadata.document_id)
        assert len(versions) >= 3  # At least versions 2, 3, 4

        # Check versions are in order
        version_numbers = [v.version for v in versions]
        assert version_numbers == sorted(version_numbers)

    @pytest.mark.asyncio
    async def test_get_versions_nonexistent_document(self, storage):
        """Test getting versions for a document that doesn't exist"""
        versions = await storage.get_versions("nonexistent-id")
        assert versions == []

    @pytest.mark.asyncio
    async def test_revert_to_version(self, storage, sample_document):
        """Test reverting a document to a previous version"""
        # Save document
        await storage.save(sample_document)

        # Save version 2
        version2 = DocumentVersion(
            version=2,
            timestamp=datetime.utcnow(),
            user="test_user",
            changes={"content": "version 2"},
            commit_message="Version 2"
        )
        await storage.save_version(sample_document.metadata.document_id, version2)

        # Update document to version 2
        sample_document.metadata.version = 2
        sample_document.content.formatted_content = "Version 2 content"
        await storage.save(sample_document)

        # Save version 3
        version3 = DocumentVersion(
            version=3,
            timestamp=datetime.utcnow(),
            user="test_user",
            changes={"content": "version 3"},
            commit_message="Version 3"
        )
        await storage.save_version(sample_document.metadata.document_id, version3)

        # Update document to version 3
        sample_document.metadata.version = 3
        sample_document.content.formatted_content = "Version 3 content"
        await storage.save(sample_document)

        # Revert to version 2
        reverted = await storage.revert_to_version(sample_document.metadata.document_id, 2)

        assert reverted is not None
        assert reverted.metadata.version == 4  # New version after revert
        assert len(reverted.history) > 0

        # Check that a revert version was created
        versions = await storage.get_versions(sample_document.metadata.document_id)
        latest_version = max(versions, key=lambda v: v.version)
        assert "reverted" in latest_version.changes.get("action", "")

    @pytest.mark.asyncio
    async def test_revert_to_nonexistent_version(self, storage, sample_document):
        """Test reverting to a version that doesn't exist"""
        await storage.save(sample_document)

        with pytest.raises(VersionNotFoundError):
            await storage.revert_to_version(sample_document.metadata.document_id, 999)

    @pytest.mark.asyncio
    async def test_revert_nonexistent_document(self, storage):
        """Test reverting a document that doesn't exist"""
        with pytest.raises(DocumentNotFoundError):
            await storage.revert_to_version("nonexistent-id", 1)

    @pytest.mark.asyncio
    async def test_health_check(self, storage, temp_dir):
        """Test health check functionality"""
        health = await storage.health_check()

        assert health["status"] == "healthy"
        assert health["storage_type"] == "filesystem"
        assert health["base_path"] == str(temp_dir)
        assert health["checks"]["base_path_exists"] is True
        assert health["checks"]["base_path_writable"] is True
        assert health["checks"]["documents_dir_exists"] is True
        assert health["checks"]["versions_dir_exists"] is True
        assert health["checks"]["metadata_dir_exists"] is True
        assert "document_count" in health
        assert "free_space_gb" in health

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, storage, sample_document, another_document):
        """Test concurrent save and load operations"""
        import asyncio

        # Perform concurrent saves
        results = await asyncio.gather(
            storage.save(sample_document),
            storage.save(another_document),
            return_exceptions=True
        )

        assert all(r is True for r in results)

        # Perform concurrent loads
        docs = await asyncio.gather(
            storage.load(sample_document.metadata.document_id),
            storage.load(another_document.metadata.document_id),
            return_exceptions=True
        )

        assert docs[0].metadata.document_id == sample_document.metadata.document_id
        assert docs[1].metadata.document_id == another_document.metadata.document_id

    @pytest.mark.asyncio
    async def test_large_document(self, storage):
        """Test handling of large documents"""
        from src.models.document import DocumentMessage, DocumentMetadata, DocumentContent, DocumentType

        # Create a large document
        large_content = "x" * (1024 * 1024)  # 1MB of content

        metadata = DocumentMetadata(
            document_id="large-doc",
            document_type=DocumentType.MARKDOWN,
            name="Large Document",
            created_user="test_user",
            updated_user="test_user",
            file_size=len(large_content)
        )

        content = DocumentContent(
            formatted_content=large_content,
            raw_text=large_content
        )

        large_doc = DocumentMessage(metadata=metadata, content=content)

        # Save and load
        result = await storage.save(large_doc)
        assert result is True

        loaded = await storage.load("large-doc")
        assert loaded is not None
        assert len(loaded.content.formatted_content) == len(large_content)


    @pytest.mark.asyncio
    async def test_save_file(self, storage, temp_dir):
        """Test saving original file to storage"""
        # Create test PDF content
        pdf_content = b"%PDF-1.4 Test PDF content"
        document_id = "test-doc-001"
        
        # Save file
        file_path = await storage.save_file(document_id, pdf_content, ".pdf")
        
        # Check file was created
        assert file_path is not None
        assert file_path == f"files/{document_id}.pdf"
        
        # Verify file exists
        full_path = temp_dir / "files" / f"{document_id}.pdf"
        assert full_path.exists()
        
        # Verify content
        with open(full_path, 'rb') as f:
            saved_content = f.read()
            assert saved_content == pdf_content

    @pytest.mark.asyncio
    async def test_get_file(self, storage, temp_dir):
        """Test retrieving original file from storage"""
        # Create test file
        pdf_content = b"%PDF-1.4 Test PDF content"
        document_id = "test-doc-002"
        
        # Save file first
        await storage.save_file(document_id, pdf_content, ".pdf")
        
        # Retrieve file
        retrieved_content = await storage.get_file(document_id, ".pdf")
        
        assert retrieved_content is not None
        assert retrieved_content == pdf_content

    @pytest.mark.asyncio
    async def test_get_nonexistent_file(self, storage):
        """Test retrieving a file that doesn't exist"""
        result = await storage.get_file("nonexistent-id", ".pdf")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_file(self, storage, temp_dir):
        """Test deleting original file from storage"""
        # Create test file
        pdf_content = b"%PDF-1.4 Test PDF content"
        document_id = "test-doc-003"
        
        # Save file first
        await storage.save_file(document_id, pdf_content, ".pdf")
        
        # Verify file exists
        full_path = temp_dir / "files" / f"{document_id}.pdf"
        assert full_path.exists()
        
        # Delete file
        success = await storage.delete_file(document_id, ".pdf")
        
        assert success is True
        assert not full_path.exists()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_file(self, storage):
        """Test deleting a file that doesn't exist"""
        success = await storage.delete_file("nonexistent-id", ".pdf")
        assert success is False

    @pytest.mark.asyncio
    async def test_save_file_multiple_extensions(self, storage, temp_dir):
        """Test saving files with different extensions"""
        document_id = "test-doc-004"
        
        # Save PDF
        pdf_content = b"%PDF-1.4 PDF content"
        pdf_path = await storage.save_file(document_id, pdf_content, ".pdf")
        assert pdf_path == f"files/{document_id}.pdf"
        
        # Save DOCX (different extension, should not overwrite PDF)
        docx_content = b"PK\x03\x04 DOCX content"
        docx_path = await storage.save_file(f"{document_id}_doc", docx_content, ".docx")
        assert docx_path == f"files/{document_id}_doc.docx"
        
        # Verify both files exist
        assert (temp_dir / "files" / f"{document_id}.pdf").exists()
        assert (temp_dir / "files" / f"{document_id}_doc.docx").exists()
