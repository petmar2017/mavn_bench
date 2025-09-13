"""Tests for RedisStorage adapter"""

import pytest
import json
from datetime import datetime

from src.storage.redis_storage import RedisStorage
from src.storage.base_storage import (
    DocumentNotFoundError,
    VersionNotFoundError,
    StorageConnectionError
)
from src.models.document import DocumentMessage, DocumentVersion


@pytest.mark.asyncio
class TestRedisStorage:
    """Test suite for RedisStorage"""

    @pytest.fixture
    async def storage(self, redis_test_client):
        """Create a RedisStorage instance for testing"""
        # This will skip if Redis is not available
        storage = RedisStorage(redis_url="redis://localhost:6379/1")
        yield storage
        # Cleanup
        if storage.redis_client:
            await storage.close()

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test storage initialization"""
        storage = RedisStorage(redis_url="redis://localhost:6379/1")
        assert storage.storage_type == "redis"
        assert storage.redis_url == "redis://localhost:6379/1"
        assert storage.key_prefix == "mavn_bench"
        assert storage.ttl_seconds == 86400

    @pytest.mark.asyncio
    async def test_connection_failure(self):
        """Test handling of connection failure"""
        storage = RedisStorage(redis_url="redis://invalid:9999/0")

        with pytest.raises(StorageConnectionError):
            await storage._ensure_connected()

    @pytest.mark.asyncio
    async def test_save_document(self, storage, sample_document):
        """Test saving a document to Redis"""
        result = await storage.save(sample_document)
        assert result is True

        # Verify document was saved
        exists = await storage.exists(sample_document.metadata.document_id)
        assert exists is True

    @pytest.mark.asyncio
    async def test_load_document(self, storage, sample_document):
        """Test loading a document from Redis"""
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
        """Test deleting a document from Redis"""
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
        """Test checking document existence in Redis"""
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
        pdf_docs = await storage.list_documents(
            document_type=str(sample_document.metadata.document_type)
        )
        assert len(pdf_docs) == 1
        assert pdf_docs[0].document_type == sample_document.metadata.document_type

        # Test pagination
        paginated = await storage.list_documents(limit=1, offset=0)
        assert len(paginated) == 1

        paginated_offset = await storage.list_documents(limit=1, offset=1)
        assert len(paginated_offset) == 1
        assert paginated[0].document_id != paginated_offset[0].document_id

    @pytest.mark.asyncio
    async def test_ttl_refresh(self, storage, sample_document):
        """Test that TTL is refreshed on document access"""
        await storage.save(sample_document)

        # Get TTL before access
        await storage._ensure_connected()
        doc_key = storage._get_document_key(sample_document.metadata.document_id)
        ttl_before = await storage.redis_client.ttl(doc_key)

        # Wait a moment
        import asyncio
        await asyncio.sleep(1)

        # Load document (should refresh TTL)
        await storage.load(sample_document.metadata.document_id)

        # Check TTL was refreshed
        ttl_after = await storage.redis_client.ttl(doc_key)
        assert ttl_after >= ttl_before

    @pytest.mark.asyncio
    async def test_save_version(self, storage, sample_document):
        """Test saving document versions in Redis"""
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
        assert len(versions) >= 1

    @pytest.mark.asyncio
    async def test_get_versions(self, storage, sample_document):
        """Test retrieving document versions from Redis"""
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
        assert len(versions) >= 3

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

        # Update document
        sample_document.metadata.version = 2
        await storage.save(sample_document)

        # Revert to version 1
        reverted = await storage.revert_to_version(sample_document.metadata.document_id, 1)

        assert reverted is not None
        assert reverted.metadata.version == 3  # New version after revert
        assert len(reverted.history) > 0

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
    async def test_health_check(self, storage):
        """Test health check functionality"""
        health = await storage.health_check()

        assert health["status"] == "healthy"
        assert health["storage_type"] == "redis"
        assert health["connected"] is True
        assert "document_count" in health
        assert "redis_version" in health
        assert "used_memory_human" in health
        assert "connected_clients" in health

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
    async def test_pipeline_operations(self, storage, sample_document):
        """Test that pipeline operations work correctly"""
        # This tests the atomic nature of pipeline operations
        await storage.save(sample_document)

        # Create multiple versions quickly
        versions = []
        for i in range(2, 6):
            version = DocumentVersion(
                version=i,
                timestamp=datetime.utcnow(),
                user="test_user",
                changes={"version": i},
                commit_message=f"Version {i}"
            )
            versions.append(version)

        # Save all versions
        results = await asyncio.gather(
            *[storage.save_version(sample_document.metadata.document_id, v) for v in versions],
            return_exceptions=True
        )

        assert all(r is True for r in results)

        # Verify all versions were saved
        saved_versions = await storage.get_versions(sample_document.metadata.document_id)
        assert len(saved_versions) >= 4

    @pytest.mark.asyncio
    async def test_connection_cleanup(self):
        """Test that connections are properly cleaned up"""
        storage = RedisStorage(redis_url="redis://localhost:6379/1")

        # Ensure connected
        await storage._ensure_connected()
        assert storage.redis_client is not None

        # Close connection
        await storage.close()
        assert storage.redis_client is None