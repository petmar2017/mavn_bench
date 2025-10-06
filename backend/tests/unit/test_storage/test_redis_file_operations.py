"""Tests for RedisStorage file operations"""

import pytest
import pytest_asyncio
from src.storage.redis_storage import RedisStorage
from src.storage.base_storage import StorageError


class TestRedisFileOperations:
    """Test suite for Redis file operations"""

    @pytest_asyncio.fixture
    async def redis_storage(self):
        """Create RedisStorage instance for testing"""
        storage = RedisStorage(redis_url="redis://localhost:6379")
        storage.key_prefix = "test_files"  # Override key_prefix for testing
        yield storage
        await storage.close()

    @pytest.mark.asyncio
    async def test_save_file(self, redis_storage):
        """Test saving a file to Redis"""
        document_id = "test-doc-001"
        file_content = b"%PDF-1.4 Test PDF content"
        extension = ".pdf"

        file_path = await redis_storage.save_file(document_id, file_content, extension)

        assert file_path == f"files/{document_id}{extension}"

    @pytest.mark.asyncio
    async def test_get_file(self, redis_storage):
        """Test retrieving a file from Redis"""
        document_id = "test-doc-002"
        file_content = b"%PDF-1.4 Test PDF content"
        extension = ".pdf"

        await redis_storage.save_file(document_id, file_content, extension)
        retrieved_content = await redis_storage.get_file(document_id, extension)

        assert retrieved_content == file_content

    @pytest.mark.asyncio
    async def test_get_nonexistent_file(self, redis_storage):
        """Test retrieving a file that doesn't exist"""
        result = await redis_storage.get_file("nonexistent-id", ".pdf")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_file(self, redis_storage):
        """Test deleting a file from Redis"""
        document_id = "test-doc-003"
        file_content = b"%PDF-1.4 Test PDF content"
        extension = ".pdf"

        await redis_storage.save_file(document_id, file_content, extension)
        success = await redis_storage.delete_file(document_id, extension)

        assert success is True

        retrieved = await redis_storage.get_file(document_id, extension)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_file(self, redis_storage):
        """Test deleting a file that doesn't exist"""
        success = await redis_storage.delete_file("nonexistent-id", ".pdf")
        assert success is False

    @pytest.mark.asyncio
    async def test_file_size_limit(self, redis_storage):
        """Test file size limit enforcement"""
        document_id = "test-doc-large"
        large_content = b"x" * (11 * 1024 * 1024)  # 11MB (over 10MB limit)
        extension = ".pdf"

        with pytest.raises(StorageError, match="File too large for Redis storage"):
            await redis_storage.save_file(document_id, large_content, extension)

    @pytest.mark.asyncio
    async def test_save_file_multiple_extensions(self, redis_storage):
        """Test saving files with different extensions"""
        document_id = "test-doc-004"

        pdf_content = b"%PDF-1.4 PDF content"
        pdf_path = await redis_storage.save_file(document_id, pdf_content, ".pdf")
        assert pdf_path == f"files/{document_id}.pdf"

        docx_content = b"PK\x03\x04 DOCX content"
        docx_path = await redis_storage.save_file(f"{document_id}_doc", docx_content, ".docx")
        assert docx_path == f"files/{document_id}_doc.docx"

        retrieved_pdf = await redis_storage.get_file(document_id, ".pdf")
        assert retrieved_pdf == pdf_content

        retrieved_docx = await redis_storage.get_file(f"{document_id}_doc", ".docx")
        assert retrieved_docx == docx_content

    @pytest.mark.asyncio
    async def test_file_base64_encoding(self, redis_storage):
        """Test that binary content is correctly encoded/decoded"""
        document_id = "test-doc-binary"
        binary_content = bytes(range(256))  # All possible byte values
        extension = ".bin"

        await redis_storage.save_file(document_id, binary_content, extension)
        retrieved = await redis_storage.get_file(document_id, extension)

        assert retrieved == binary_content
        assert len(retrieved) == 256

    @pytest.mark.asyncio
    async def test_empty_file(self, redis_storage):
        """Test saving and retrieving an empty file"""
        document_id = "test-doc-empty"
        empty_content = b""
        extension = ".txt"

        file_path = await redis_storage.save_file(document_id, empty_content, extension)
        assert file_path == f"files/{document_id}{extension}"

        retrieved = await redis_storage.get_file(document_id, extension)
        assert retrieved == empty_content

    @pytest.mark.asyncio
    async def test_file_overwrite(self, redis_storage):
        """Test overwriting an existing file"""
        document_id = "test-doc-overwrite"
        original_content = b"Original content"
        new_content = b"New content"
        extension = ".txt"

        await redis_storage.save_file(document_id, original_content, extension)
        await redis_storage.save_file(document_id, new_content, extension)

        retrieved = await redis_storage.get_file(document_id, extension)
        assert retrieved == new_content
