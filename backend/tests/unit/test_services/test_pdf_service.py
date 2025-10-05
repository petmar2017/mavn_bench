"""Tests for PDFService"""

import pytest
import os
import tempfile
from pathlib import Path

from src.services.pdf_service import PDFService
from src.models.document import DocumentType


class TestPDFService:
    """Test suite for PDFService"""

    @pytest.fixture
    def service(self):
        """Create a PDFService instance for testing"""
        return PDFService()

    @pytest.fixture
    def sample_pdf_path(self, tmp_path):
        """Create a sample PDF file for testing"""
        pdf_file = tmp_path / "test.pdf"

        # Create a minimal valid PDF
        pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources 4 0 R /MediaBox [0 0 612 792] /Contents 5 0 R >>
endobj
4 0 obj
<< /Font << /F1 6 0 R >> >>
endobj
5 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF) Tj
ET
endstream
endobj
6 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
xref
0 7
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000229 00000 n
0000000274 00000 n
0000000367 00000 n
trailer
<< /Size 7 /Root 1 0 R >>
startxref
450
%%EOF"""
        pdf_file.write_bytes(pdf_content)
        return str(pdf_file)

    @pytest.fixture
    def non_pdf_file(self, tmp_path):
        """Create a non-PDF file for testing"""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("This is not a PDF")
        return str(txt_file)

    @pytest.mark.asyncio
    async def test_pdf_to_markdown_basic(self, service, sample_pdf_path):
        """Test basic PDF to markdown conversion"""
        # Since we don't have PyMuPDF in tests, this will use fallback
        markdown = await service.pdf_to_markdown(sample_pdf_path)

        assert markdown is not None
        assert isinstance(markdown, str)
        assert len(markdown) > 0

    @pytest.mark.asyncio
    async def test_pdf_to_markdown_file_not_found(self, service):
        """Test PDF conversion with non-existent file"""
        with pytest.raises(FileNotFoundError, match="PDF file not found"):
            await service.pdf_to_markdown("/nonexistent/file.pdf")

    @pytest.mark.asyncio
    async def test_pdf_to_markdown_invalid_file(self, service, non_pdf_file):
        """Test PDF conversion with non-PDF file"""
        with pytest.raises(ValueError, match="File is not a PDF"):
            await service.pdf_to_markdown(non_pdf_file)

    @pytest.mark.asyncio
    async def test_extract_metadata(self, service, sample_pdf_path):
        """Test extracting metadata from PDF"""
        metadata = await service.extract_metadata(sample_pdf_path)

        assert metadata is not None
        assert "file_path" in metadata
        assert "file_size" in metadata
        assert "file_name" in metadata
        assert metadata["file_name"] == "test.pdf"
        assert metadata["file_size"] > 0

    @pytest.mark.asyncio
    async def test_extract_metadata_file_not_found(self, service):
        """Test metadata extraction with non-existent file"""
        with pytest.raises(FileNotFoundError, match="PDF file not found"):
            await service.extract_metadata("/nonexistent/file.pdf")

    @pytest.mark.asyncio
    async def test_extract_tables(self, service, sample_pdf_path):
        """Test extracting tables from PDF"""
        tables = await service.extract_tables(sample_pdf_path)

        assert tables is not None
        assert isinstance(tables, list)
        # Without PyMuPDF, should return empty list
        assert len(tables) == 0

    @pytest.mark.asyncio
    async def test_extract_tables_file_not_found(self, service):
        """Test table extraction with non-existent file"""
        with pytest.raises(FileNotFoundError, match="PDF file not found"):
            await service.extract_tables("/nonexistent/file.pdf")

    @pytest.mark.asyncio
    async def test_process_pdf_document(self, service, sample_pdf_path):
        """Test processing a PDF into a DocumentMessage"""
        document = await service.process_pdf_document(sample_pdf_path, "test_user")

        assert document is not None
        assert document.metadata.document_type == DocumentType.PDF
        assert document.metadata.name == "test.pdf"
        assert document.metadata.created_user == "test_user"
        assert document.content.formatted_content is not None
        assert "pdf_reader" in document.tools
        assert "table_extractor" in document.tools

    @pytest.mark.asyncio
    async def test_extract_images(self, service, sample_pdf_path, tmp_path):
        """Test extracting images from PDF"""
        output_dir = str(tmp_path / "images")
        os.makedirs(output_dir, exist_ok=True)

        image_paths = await service.extract_images(sample_pdf_path, output_dir)

        assert image_paths is not None
        assert isinstance(image_paths, list)
        # Without PyMuPDF, should return empty list
        assert len(image_paths) == 0

    @pytest.mark.asyncio
    async def test_extract_images_default_output_dir(self, service, sample_pdf_path):
        """Test extracting images with default output directory"""
        image_paths = await service.extract_images(sample_pdf_path)

        assert image_paths is not None
        assert isinstance(image_paths, list)

    @pytest.mark.asyncio
    async def test_extract_images_file_not_found(self, service):
        """Test image extraction with non-existent file"""
        with pytest.raises(FileNotFoundError, match="PDF file not found"):
            await service.extract_images("/nonexistent/file.pdf")

    def test_table_to_markdown(self, service):
        """Test converting table data to markdown"""
        table_data = [
            ["Header 1", "Header 2", "Header 3"],
            ["Row 1 Col 1", "Row 1 Col 2", "Row 1 Col 3"],
            ["Row 2 Col 1", "Row 2 Col 2", "Row 2 Col 3"]
        ]

        markdown = service._table_to_markdown(table_data)

        assert "| Header 1 | Header 2 | Header 3 |" in markdown
        assert "| --- | --- | --- |" in markdown
        assert "| Row 1 Col 1 | Row 1 Col 2 | Row 1 Col 3 |" in markdown

    def test_table_to_markdown_empty(self, service):
        """Test converting empty table data"""
        markdown = service._table_to_markdown([])
        assert markdown == ""

    def test_basic_pdf_extract_fallback(self, service, sample_pdf_path):
        """Test the basic PDF extraction fallback method"""
        text = service._basic_pdf_extract(sample_pdf_path)

        assert text is not None
        # Our test PDF contains "Test PDF"
        assert "Test PDF" in text or "PDF" in text
        # The text should have some content
        assert len(text) > 10

    @pytest.mark.asyncio
    async def test_health_check(self, service):
        """Test service health check"""
        health = await service.health_check()

        assert health["service"] == "PDFService"
        assert health["status"] in ["healthy", "degraded"]
        assert "dependencies" in health
        assert "PyMuPDF" in health["dependencies"]
        assert "supported_formats" in health
        assert ".pdf" in health["supported_formats"]
        assert "timestamp" in health

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, service, sample_pdf_path):
        """Test concurrent PDF operations"""
        import asyncio

        # Run multiple operations concurrently
        results = await asyncio.gather(
            service.pdf_to_markdown(sample_pdf_path),
            service.extract_metadata(sample_pdf_path),
            service.extract_tables(sample_pdf_path),
            return_exceptions=True
        )

        # All should succeed
        assert all(not isinstance(r, Exception) for r in results)
        assert results[0] is not None  # markdown
        assert results[1] is not None  # metadata
        assert isinstance(results[2], list)  # tables

    def test_supported_formats(self, service):
        """Test that service reports supported formats"""
        assert service.supported_formats == [".pdf"]