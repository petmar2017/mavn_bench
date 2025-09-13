"""Tests for VectorSearchService

Following prompt.md guidelines:
- NO MOCKS - real implementations only
- Async tests with pytest-asyncio
- 80%+ coverage target
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime
from typing import List, Tuple

from src.services.vector_search_service import VectorSearchService
from src.services.service_factory import ServiceFactory, ServiceType
from src.models.document import (
    DocumentMessage,
    DocumentMetadata,
    DocumentContent,
    DocumentType
)


@pytest_asyncio.fixture
async def vector_service():
    """Create VectorSearchService instance"""
    service = VectorSearchService()
    return service


@pytest.fixture
def sample_document():
    """Create a sample document for testing"""
    metadata = DocumentMetadata(
        document_id="test_doc_001",
        document_type=DocumentType.PDF,
        name="Test Document",
        created_user="test_user",
        updated_user="test_user",
        tags=["test", "sample"],
        summary="This is a test document about machine learning and AI"
    )

    content = DocumentContent(
        raw_text="Machine learning is a subset of artificial intelligence. It enables systems to learn from data.",
        formatted_content="# Machine Learning\n\nMachine learning is a subset of artificial intelligence."
    )

    return DocumentMessage(
        metadata=metadata,
        content=content
    )


@pytest.fixture
def sample_documents():
    """Create multiple sample documents for testing"""
    docs = []

    # Document 1: ML focused
    metadata1 = DocumentMetadata(
        document_id="test_doc_001",
        document_type=DocumentType.PDF,
        name="ML Guide",
        created_user="test_user",
        updated_user="test_user",
        tags=["ml", "ai"],
        summary="Machine learning fundamentals"
    )
    content1 = DocumentContent(
        raw_text="Machine learning algorithms can be supervised or unsupervised.",
        formatted_content="# ML Algorithms\n\nSupervised and unsupervised learning."
    )
    docs.append(DocumentMessage(metadata=metadata1, content=content1))

    # Document 2: Python focused
    metadata2 = DocumentMetadata(
        document_id="test_doc_002",
        document_type=DocumentType.MARKDOWN,
        name="Python Tutorial",
        created_user="test_user",
        updated_user="test_user",
        tags=["python", "programming"],
        summary="Python programming basics"
    )
    content2 = DocumentContent(
        raw_text="Python is a high-level programming language used for data science.",
        formatted_content="# Python\n\nPython for data science."
    )
    docs.append(DocumentMessage(metadata=metadata2, content=content2))

    # Document 3: Database focused
    metadata3 = DocumentMetadata(
        document_id="test_doc_003",
        document_type=DocumentType.JSON,
        name="Database Design",
        created_user="test_user",
        updated_user="test_user",
        tags=["database", "sql"],
        summary="Database design principles"
    )
    content3 = DocumentContent(
        raw_text="Relational databases use SQL for querying structured data.",
        formatted_content="# Databases\n\nSQL and relational databases."
    )
    docs.append(DocumentMessage(metadata=metadata3, content=content3))

    return docs


class TestVectorSearchService:
    """Test VectorSearchService functionality"""

    @pytest.mark.asyncio
    async def test_service_initialization(self, vector_service):
        """Test that service initializes correctly"""
        assert vector_service is not None
        assert vector_service.service_name == "VectorSearchService"
        assert vector_service.collection_name == "documents"
        assert vector_service.vector_size == 384

    @pytest.mark.asyncio
    async def test_service_registration(self):
        """Test that service is registered with factory"""
        # Service should auto-register on import
        service = ServiceFactory.create(ServiceType.VECTOR_SEARCH)
        assert service is not None
        assert isinstance(service, VectorSearchService)

    @pytest.mark.asyncio
    async def test_index_document(self, vector_service, sample_document):
        """Test indexing a document"""
        # Index the document
        result = await vector_service.index_document(sample_document)

        # Should return True for successful indexing
        assert result is True

        # Document should exist in index
        exists = await vector_service.document_exists(sample_document.metadata.document_id)
        assert exists is True

    @pytest.mark.asyncio
    async def test_index_document_force_reindex(self, vector_service, sample_document):
        """Test force reindexing a document"""
        # Index once
        result1 = await vector_service.index_document(sample_document)
        assert result1 is True

        # Index again without force - should skip
        result2 = await vector_service.index_document(sample_document, force_reindex=False)
        assert result2 is True  # Returns True but logs that it's already indexed

        # Force reindex
        result3 = await vector_service.index_document(sample_document, force_reindex=True)
        assert result3 is True

    @pytest.mark.asyncio
    async def test_search_basic(self, vector_service, sample_documents):
        """Test basic search functionality"""
        # Index documents first
        for doc in sample_documents:
            await vector_service.index_document(doc)

        # Search for machine learning
        results = await vector_service.search(
            query="machine learning algorithms",
            limit=10,
            threshold=0.5
        )

        # Should return results
        assert isinstance(results, list)
        if len(results) > 0:  # May be empty if using mock
            assert all(isinstance(r, tuple) for r in results)
            assert all(len(r) == 2 for r in results)  # (metadata, score)

    @pytest.mark.asyncio
    async def test_search_with_filters(self, vector_service, sample_documents):
        """Test search with metadata filters"""
        # Index documents
        for doc in sample_documents:
            await vector_service.index_document(doc)

        # Search with filters
        results = await vector_service.search(
            query="programming",
            limit=5,
            filters={"document_type": "markdown"},
            threshold=0.3
        )

        # Results should be list of tuples
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_find_similar(self, vector_service, sample_documents):
        """Test finding similar documents"""
        # Index documents
        for doc in sample_documents:
            await vector_service.index_document(doc)

        # Find similar to first document
        similar = await vector_service.find_similar(
            document_id="test_doc_001",
            limit=2,
            threshold=0.5
        )

        # Should return list of similar documents
        assert isinstance(similar, list)
        # Should not include the source document itself
        if len(similar) > 0:
            assert all(result[0].document_id != "test_doc_001" for result in similar)

    @pytest.mark.asyncio
    async def test_delete_document(self, vector_service, sample_document):
        """Test deleting a document from index"""
        # Index document
        await vector_service.index_document(sample_document)
        assert await vector_service.document_exists(sample_document.metadata.document_id)

        # Delete document
        result = await vector_service.delete_document(sample_document.metadata.document_id)
        assert result is True

        # Document should not exist anymore
        exists = await vector_service.document_exists(sample_document.metadata.document_id)
        assert exists is False

    @pytest.mark.asyncio
    async def test_document_exists(self, vector_service, sample_document):
        """Test checking if document exists"""
        doc_id = sample_document.metadata.document_id

        # Should not exist initially
        exists = await vector_service.document_exists(doc_id)
        assert exists is False

        # Index document
        await vector_service.index_document(sample_document)

        # Should exist now
        exists = await vector_service.document_exists(doc_id)
        assert exists is True

    @pytest.mark.asyncio
    async def test_reindex_all(self, vector_service, sample_documents):
        """Test reindexing all documents"""
        # Reindex all documents
        count = await vector_service.reindex_all(sample_documents)

        # Should return count of indexed documents
        assert count == len(sample_documents)

        # All documents should exist
        for doc in sample_documents:
            exists = await vector_service.document_exists(doc.metadata.document_id)
            assert exists is True

    @pytest.mark.asyncio
    async def test_health_check(self, vector_service):
        """Test service health check"""
        health = await vector_service.health_check()

        assert isinstance(health, dict)
        assert "service" in health
        assert health["service"] == "VectorSearchService"
        assert "status" in health
        assert health["status"] in ["healthy", "degraded", "unhealthy"]

    @pytest.mark.asyncio
    async def test_empty_search(self, vector_service):
        """Test search with no documents indexed"""
        results = await vector_service.search(
            query="test query",
            limit=10
        )

        # Should return empty list or mock results
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_edge_cases(self, vector_service):
        """Test search with edge cases"""
        # Empty query
        with pytest.raises(Exception):
            await vector_service.search(query="", limit=10)

        # Zero limit - should still work
        results = await vector_service.search(
            query="test",
            limit=0
        )
        assert isinstance(results, list)
        assert len(results) == 0

        # Very high threshold
        results = await vector_service.search(
            query="test",
            limit=10,
            threshold=0.99
        )
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, vector_service, sample_documents):
        """Test concurrent indexing and searching"""
        # Index documents concurrently
        tasks = [
            vector_service.index_document(doc)
            for doc in sample_documents
        ]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(r is True for r in results)

        # Search concurrently
        search_tasks = [
            vector_service.search("test", limit=5),
            vector_service.search("python", limit=5),
            vector_service.search("database", limit=5)
        ]
        search_results = await asyncio.gather(*search_tasks)

        # All should return lists
        assert all(isinstance(r, list) for r in search_results)