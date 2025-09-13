"""Pytest configuration and shared fixtures"""

import asyncio
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Generator, Any

from src.models.document import (
    DocumentMessage,
    DocumentMetadata,
    DocumentContent,
    DocumentType,
    AccessPermission,
    AccessGroup
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup after test
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def sample_document() -> DocumentMessage:
    """Create a sample document for testing"""
    metadata = DocumentMetadata(
        document_id="test-doc-001",
        document_type=DocumentType.PDF,
        name="Test Document",
        summary="This is a test document",
        access_permission=AccessPermission.READ,
        access_group=AccessGroup.ME,
        created_user="test_user",
        updated_user="test_user",
        version=1,
        tags=["test", "sample"],
        file_size=1024,
        mime_type="application/pdf"
    )

    content = DocumentContent(
        formatted_content="# Test Document\n\nThis is the content.",
        raw_text="Test Document. This is the content.",
        structured_data={"key": "value"},
        embeddings=[0.1, 0.2, 0.3, 0.4, 0.5]
    )

    return DocumentMessage(
        metadata=metadata,
        content=content,
        tools=["pdf_reader", "text_extractor"],
        trace_id="trace-123",
        span_id="span-456",
        session_id="session-789",
        user_id="test_user"
    )


@pytest.fixture
def another_document() -> DocumentMessage:
    """Create another sample document for testing"""
    metadata = DocumentMetadata(
        document_id="test-doc-002",
        document_type=DocumentType.MARKDOWN,
        name="Another Test Document",
        summary="This is another test document",
        access_permission=AccessPermission.WRITE,
        access_group=AccessGroup.GROUP,
        created_user="another_user",
        updated_user="another_user",
        version=1,
        tags=["test", "markdown"],
        file_size=512,
        mime_type="text/markdown"
    )

    content = DocumentContent(
        formatted_content="## Another Document\n\nDifferent content here.",
        raw_text="Another Document. Different content here."
    )

    return DocumentMessage(
        metadata=metadata,
        content=content,
        user_id="another_user"
    )


@pytest.fixture
async def redis_test_client():
    """Create a Redis client for testing (if Redis is available)"""
    import redis.asyncio as redis
    from redis.exceptions import ConnectionError as RedisConnectionError

    # Use a different database for testing (db=1)
    test_redis_url = "redis://localhost:6379/1"

    try:
        client = redis.from_url(test_redis_url, encoding="utf-8", decode_responses=True)
        # Test connection
        await client.ping()
        yield client
        # Cleanup: flush test database
        await client.flushdb()
        await client.close()
    except (RedisConnectionError, OSError):
        # Redis not available, skip Redis tests
        pytest.skip("Redis not available for testing")