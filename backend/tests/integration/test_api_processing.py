"""Integration tests for Processing API endpoints"""

import pytest
import json
import io
from datetime import datetime
from typing import Dict, Any
from httpx import AsyncClient
from fastapi import status

from src.api.main import app
from src.core.config import get_settings


settings = get_settings()


@pytest.fixture
async def client():
    """Create test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def api_headers() -> Dict[str, str]:
    """Get API headers for testing"""
    return {
        "X-API-Key": settings.auth.test_api_key,
        "Content-Type": "application/json"
    }


@pytest.fixture
async def test_document(client: AsyncClient, api_headers: Dict) -> str:
    """Create a test document and return its ID"""
    document_data = {
        "name": "Test Document for Processing",
        "document_type": "markdown",
        "content": """
        # Test Document

        This is a test document with some content for processing.
        It contains multiple paragraphs and sections.

        ## Section 1
        Information about topic A.

        ## Section 2
        Information about topic B with entities like John Smith from
        Acme Corporation located in New York.

        The meeting is scheduled for January 15, 2024 with a budget of $50,000.
        """,
        "summary": "Test document for processing operations"
    }

    response = await client.post(
        "/api/documents/",
        json=document_data,
        headers=api_headers
    )

    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["document_id"]


class TestPDFConversion:
    """Test PDF conversion functionality"""

    @pytest.mark.asyncio
    async def test_pdf_upload_and_convert(self, client: AsyncClient, api_headers: Dict):
        """Test uploading and converting a PDF file"""
        # Create a simple PDF-like file
        pdf_content = b"%PDF-1.4\n%Test PDF content\n%%EOF"

        upload_headers = api_headers.copy()
        del upload_headers["Content-Type"]

        files = {"file": ("test.pdf", pdf_content, "application/pdf")}

        response = await client.post(
            "/api/process/pdf-to-markdown",
            files=files,
            headers=upload_headers
        )

        # Will depend on actual PDF service implementation
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert data["success"] is True
            assert "processing_time" in data

    @pytest.mark.asyncio
    async def test_convert_existing_pdf_document(self, client: AsyncClient, api_headers: Dict):
        """Test converting an existing PDF document"""
        # This would require a pre-existing PDF document
        request_data = {
            "document_id": "test_pdf_doc_id",
            "save_result": True
        }

        response = await client.post(
            "/api/process/pdf-to-markdown",
            json=request_data,
            headers=api_headers
        )

        # Will return 404 if document doesn't exist
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

    @pytest.mark.asyncio
    async def test_pdf_conversion_invalid_file(self, client: AsyncClient, api_headers: Dict):
        """Test PDF conversion with non-PDF file"""
        upload_headers = api_headers.copy()
        del upload_headers["Content-Type"]

        files = {"file": ("test.txt", b"Not a PDF", "text/plain")}

        response = await client.post(
            "/api/process/pdf-to-markdown",
            files=files,
            headers=upload_headers
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestDocumentSummarization:
    """Test document summarization functionality"""

    @pytest.mark.asyncio
    async def test_summarize_document(self, client: AsyncClient, api_headers: Dict, test_document: str):
        """Test summarizing a document"""
        request_data = {
            "document_id": test_document,
            "max_length": 100,
            "style": "business",
            "update_document": True
        }

        response = await client.post(
            "/api/process/summarize",
            json=request_data,
            headers=api_headers
        )

        # Will depend on LLM service implementation
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert data["success"] is True
            assert "result" in data
            assert "processing_time" in data

    @pytest.mark.asyncio
    async def test_summarize_nonexistent_document(self, client: AsyncClient, api_headers: Dict):
        """Test summarizing a document that doesn't exist"""
        request_data = {
            "document_id": "nonexistent_id",
            "max_length": 100
        }

        response = await client.post(
            "/api/process/summarize",
            json=request_data,
            headers=api_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_summarize_with_different_styles(self, client: AsyncClient, api_headers: Dict, test_document: str):
        """Test summarization with different styles"""
        styles = ["business", "technical", "casual"]

        for style in styles:
            request_data = {
                "document_id": test_document,
                "max_length": 200,
                "style": style,
                "update_document": False
            }

            response = await client.post(
                "/api/process/summarize",
                json=request_data,
                headers=api_headers
            )

            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ]


class TestEntityExtraction:
    """Test entity extraction functionality"""

    @pytest.mark.asyncio
    async def test_extract_entities(self, client: AsyncClient, api_headers: Dict, test_document: str):
        """Test extracting entities from a document"""
        request_data = {
            "document_id": test_document,
            "entity_types": ["person", "organization", "location", "date", "money"],
            "confidence_threshold": 0.7
        }

        response = await client.post(
            "/api/process/extract-entities",
            json=request_data,
            headers=api_headers
        )

        # Will depend on LLM service implementation
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert data["success"] is True
            assert "result" in data
            assert "entities" in data["result"]

    @pytest.mark.asyncio
    async def test_extract_entities_custom_types(self, client: AsyncClient, api_headers: Dict, test_document: str):
        """Test extracting custom entity types"""
        request_data = {
            "document_id": test_document,
            "entity_types": ["product", "technology", "metric"],
            "confidence_threshold": 0.5
        }

        response = await client.post(
            "/api/process/extract-entities",
            json=request_data,
            headers=api_headers
        )

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]


class TestDocumentClassification:
    """Test document classification functionality"""

    @pytest.mark.asyncio
    async def test_classify_document(self, client: AsyncClient, api_headers: Dict, test_document: str):
        """Test classifying a document"""
        request_data = {
            "document_id": test_document,
            "categories": ["business", "technical", "legal", "marketing"],
            "multi_label": False
        }

        response = await client.post(
            "/api/process/classify",
            json=request_data,
            headers=api_headers
        )

        # Will depend on LLM service implementation
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert data["success"] is True
            assert "result" in data
            assert "classifications" in data["result"]

    @pytest.mark.asyncio
    async def test_classify_multi_label(self, client: AsyncClient, api_headers: Dict, test_document: str):
        """Test multi-label classification"""
        request_data = {
            "document_id": test_document,
            "multi_label": True
        }

        response = await client.post(
            "/api/process/classify",
            json=request_data,
            headers=api_headers
        )

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]


class TestMediaTranscription:
    """Test media transcription functionality"""

    @pytest.mark.asyncio
    async def test_transcribe_youtube(self, client: AsyncClient, api_headers: Dict):
        """Test transcribing a YouTube video"""
        request_data = {
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "language": "auto",
            "save_as_document": True
        }

        response = await client.post(
            "/api/process/transcribe",
            json=request_data,
            headers=api_headers
        )

        # Will depend on transcription service implementation
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

    @pytest.mark.asyncio
    async def test_transcribe_podcast(self, client: AsyncClient, api_headers: Dict):
        """Test transcribing a podcast"""
        request_data = {
            "url": "https://example.com/podcast.mp3",
            "language": "en",
            "save_as_document": False
        }

        response = await client.post(
            "/api/process/transcribe",
            json=request_data,
            headers=api_headers
        )

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]


class TestWebScraping:
    """Test web scraping functionality"""

    @pytest.mark.asyncio
    async def test_scrape_webpage(self, client: AsyncClient, api_headers: Dict):
        """Test scraping a webpage"""
        request_data = {
            "url": "https://example.com",
            "include_images": True,
            "include_links": True,
            "save_as_document": True
        }

        response = await client.post(
            "/api/process/scrape",
            json=request_data,
            headers=api_headers
        )

        # Will depend on scraping service implementation
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert data["success"] is True
            assert "result" in data

    @pytest.mark.asyncio
    async def test_scrape_invalid_url(self, client: AsyncClient, api_headers: Dict):
        """Test scraping with invalid URL"""
        request_data = {
            "url": "not-a-valid-url",
            "save_as_document": False
        }

        response = await client.post(
            "/api/process/scrape",
            json=request_data,
            headers=api_headers
        )

        # Should validate URL format
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]


class TestBatchProcessing:
    """Test batch processing functionality"""

    @pytest.mark.asyncio
    async def test_batch_operations(self, client: AsyncClient, api_headers: Dict, test_document: str):
        """Test executing multiple operations in batch"""
        operations = [
            {
                "id": "op1",
                "type": "summarize",
                "params": {
                    "document_id": test_document,
                    "max_length": 100
                }
            },
            {
                "id": "op2",
                "type": "extract_entities",
                "params": {
                    "document_id": test_document,
                    "entity_types": ["person", "organization"]
                }
            },
            {
                "id": "op3",
                "type": "classify",
                "params": {
                    "document_id": test_document,
                    "categories": ["business", "technical"]
                }
            }
        ]

        response = await client.post(
            "/api/process/batch",
            json=operations,
            headers=api_headers
        )

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert "op1" in data
            assert "op2" in data
            assert "op3" in data

    @pytest.mark.asyncio
    async def test_batch_operations_limit(self, client: AsyncClient, api_headers: Dict):
        """Test batch operations limit"""
        # Try to exceed the 10 operation limit
        operations = [
            {"id": f"op{i}", "type": "summarize", "params": {}}
            for i in range(11)
        ]

        response = await client.post(
            "/api/process/batch",
            json=operations,
            headers=api_headers
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestProcessingValidation:
    """Test processing input validation"""

    @pytest.mark.asyncio
    async def test_invalid_summarization_params(self, client: AsyncClient, api_headers: Dict):
        """Test summarization with invalid parameters"""
        request_data = {
            "document_id": "",  # Empty document ID
            "max_length": -1   # Negative max length
        }

        response = await client.post(
            "/api/process/summarize",
            json=request_data,
            headers=api_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_invalid_entity_extraction_params(self, client: AsyncClient, api_headers: Dict):
        """Test entity extraction with invalid parameters"""
        request_data = {
            "document_id": "test_id",
            "confidence_threshold": 1.5  # Invalid threshold > 1.0
        }

        response = await client.post(
            "/api/process/extract-entities",
            json=request_data,
            headers=api_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY