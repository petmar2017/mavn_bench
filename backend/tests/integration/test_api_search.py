"""Integration tests for Search API endpoints

Following prompt.md guidelines:
- NO MOCKS - real implementations only
- Test actual API endpoints
- Async tests with pytest-asyncio
"""

import pytest
from httpx import AsyncClient
from fastapi import status

from src.api.main import app
from src.services.service_factory import ServiceFactory, ServiceType
from src.models.document import (
    DocumentMessage,
    DocumentMetadata,
    DocumentContent,
    DocumentType
)


@pytest.fixture
async def async_client():
    """Create async test client"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def indexed_documents():
    """Create and index sample documents for testing"""
    # Get services
    doc_service = ServiceFactory.create(ServiceType.DOCUMENT)
    vector_service = ServiceFactory.create(ServiceType.VECTOR_SEARCH)

    documents = []

    # Create document 1: AI/ML focused
    metadata1 = DocumentMetadata(
        document_id="search_test_001",
        document_type=DocumentType.PDF,
        name="AI Research Paper",
        created_user="test_user",
        updated_user="test_user",
        tags=["ai", "research", "machine-learning"],
        summary="Research on artificial intelligence and machine learning applications"
    )
    content1 = DocumentContent(
        raw_text="Artificial intelligence and machine learning are transforming industries. Deep learning models achieve state-of-the-art results.",
        formatted_content="# AI Research\n\nArtificial intelligence and machine learning innovations."
    )
    doc1 = DocumentMessage(metadata=metadata1, content=content1)
    documents.append(doc1)

    # Create document 2: Python programming
    metadata2 = DocumentMetadata(
        document_id="search_test_002",
        document_type=DocumentType.MARKDOWN,
        name="Python Guide",
        created_user="test_user",
        updated_user="test_user",
        tags=["python", "programming", "tutorial"],
        summary="Comprehensive Python programming guide"
    )
    content2 = DocumentContent(
        raw_text="Python is a versatile programming language. It's widely used in data science, web development, and automation.",
        formatted_content="# Python Guide\n\nPython programming fundamentals."
    )
    doc2 = DocumentMessage(metadata=metadata2, content=content2)
    documents.append(doc2)

    # Create document 3: Database systems
    metadata3 = DocumentMetadata(
        document_id="search_test_003",
        document_type=DocumentType.JSON,
        name="Database Architecture",
        created_user="test_user",
        updated_user="test_user",
        tags=["database", "architecture", "sql"],
        summary="Modern database architecture patterns"
    )
    content3 = DocumentContent(
        raw_text="Database systems provide structured data storage. SQL databases use relational models while NoSQL offers flexible schemas.",
        formatted_content="# Database Systems\n\nSQL and NoSQL architectures."
    )
    doc3 = DocumentMessage(metadata=metadata3, content=content3)
    documents.append(doc3)

    # Store and index documents
    for doc in documents:
        await doc_service.create_document(doc)
        await vector_service.index_document(doc, force_reindex=True)

    yield documents

    # Cleanup
    for doc in documents:
        try:
            await doc_service.delete_document(doc.metadata.document_id)
            await vector_service.delete_document(doc.metadata.document_id)
        except:
            pass


class TestSearchAPI:
    """Test Search API endpoints"""

    @pytest.mark.asyncio
    async def test_vector_search_basic(self, async_client, indexed_documents):
        """Test basic vector search endpoint"""
        response = await async_client.post(
            "/api/search/vector",
            json={
                "query": "machine learning and artificial intelligence",
                "limit": 10,
                "threshold": 0.3
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "query" in data
        assert "results" in data
        assert "count" in data
        assert "search_type" in data
        assert data["search_type"] == "vector"
        assert isinstance(data["results"], list)

    @pytest.mark.asyncio
    async def test_vector_search_with_filters(self, async_client, indexed_documents):
        """Test vector search with metadata filters"""
        response = await async_client.post(
            "/api/search/vector",
            json={
                "query": "programming",
                "limit": 5,
                "threshold": 0.5,
                "filters": {"document_type": "markdown"}
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data["results"], list)

    @pytest.mark.asyncio
    async def test_find_similar_documents(self, async_client, indexed_documents):
        """Test finding similar documents endpoint"""
        response = await async_client.post(
            "/api/search/similar",
            json={
                "document_id": "search_test_001",
                "limit": 2,
                "threshold": 0.3
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "results" in data
        assert data["search_type"] == "similarity"
        assert isinstance(data["results"], list)

    @pytest.mark.asyncio
    async def test_fulltext_search(self, async_client):
        """Test fulltext search endpoint (mock implementation)"""
        response = await async_client.post(
            "/api/search/fulltext?query=test&limit=10&offset=0"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["search_type"] == "fulltext"
        assert isinstance(data["results"], list)

    @pytest.mark.asyncio
    async def test_graph_search(self, async_client):
        """Test graph search endpoint (mock implementation)"""
        response = await async_client.post(
            "/api/search/graph?query=relationships&max_depth=2&limit=10"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["search_type"] == "graph"
        assert isinstance(data["results"], list)

    @pytest.mark.asyncio
    async def test_hybrid_search(self, async_client, indexed_documents):
        """Test hybrid search combining multiple strategies"""
        response = await async_client.post(
            "/api/search/hybrid?query=python%20programming&limit=10",
            params={"search_types": ["vector", "fulltext"]}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["search_type"] == "hybrid"
        assert isinstance(data["results"], list)

    @pytest.mark.asyncio
    async def test_index_document(self, async_client):
        """Test document indexing endpoint"""
        # First create a document
        doc_response = await async_client.post(
            "/api/documents",
            json={
                "name": "Index Test Document",
                "document_type": "pdf",
                "content": "This is a test document for indexing"
            }
        )
        assert doc_response.status_code == status.HTTP_200_OK
        doc_id = doc_response.json()["document_id"]

        # Index the document
        response = await async_client.post(
            f"/api/search/index/{doc_id}?force_reindex=true"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["document_id"] == doc_id
        assert "indexed" in data
        assert "message" in data

        # Cleanup
        await async_client.delete(f"/api/documents/{doc_id}")

    @pytest.mark.asyncio
    async def test_remove_from_index(self, async_client, indexed_documents):
        """Test removing document from index"""
        doc_id = indexed_documents[0].metadata.document_id

        response = await async_client.delete(
            f"/api/search/index/{doc_id}"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["document_id"] == doc_id
        assert "removed" in data
        assert "message" in data

    @pytest.mark.asyncio
    async def test_search_empty_query(self, async_client):
        """Test search with empty query"""
        response = await async_client.post(
            "/api/search/vector",
            json={
                "query": "",
                "limit": 10
            }
        )

        # Should fail validation or return error
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

    @pytest.mark.asyncio
    async def test_search_invalid_limit(self, async_client):
        """Test search with invalid limit"""
        response = await async_client.post(
            "/api/search/vector",
            json={
                "query": "test",
                "limit": -1
            }
        )

        # Should fail validation
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_search_invalid_threshold(self, async_client):
        """Test search with invalid threshold"""
        response = await async_client.post(
            "/api/search/vector",
            json={
                "query": "test",
                "limit": 10,
                "threshold": 1.5  # Outside 0-1 range
            }
        )

        # Should fail validation
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_index_nonexistent_document(self, async_client):
        """Test indexing a document that doesn't exist"""
        response = await async_client.post(
            "/api/search/index/nonexistent_doc_id"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_search_response_structure(self, async_client, indexed_documents):
        """Test that search response has correct structure"""
        response = await async_client.post(
            "/api/search/vector",
            json={
                "query": "database systems",
                "limit": 5
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check response structure
        assert "query" in data
        assert "results" in data
        assert "count" in data
        assert "search_type" in data

        # Check results structure if any results returned
        if len(data["results"]) > 0:
            result = data["results"][0]
            assert "document_id" in result
            assert "name" in result
            assert "document_type" in result
            assert "score" in result
            assert "created_user" in result
            assert "tags" in result

    @pytest.mark.asyncio
    async def test_concurrent_searches(self, async_client, indexed_documents):
        """Test multiple concurrent search requests"""
        import asyncio

        # Create multiple search tasks
        tasks = [
            async_client.post("/api/search/vector", json={
                "query": "machine learning",
                "limit": 5
            }),
            async_client.post("/api/search/vector", json={
                "query": "python programming",
                "limit": 5
            }),
            async_client.post("/api/search/vector", json={
                "query": "database",
                "limit": 5
            })
        ]

        # Execute concurrently
        responses = await asyncio.gather(*tasks)

        # All should succeed
        for response in responses:
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "results" in data
            assert isinstance(data["results"], list)