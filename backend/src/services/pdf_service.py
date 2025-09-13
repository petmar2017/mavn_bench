"""PDF processing service with markdown conversion"""

import asyncio
import os
from typing import Dict, List, Optional, Any
from pathlib import Path
import tempfile
from datetime import datetime

from .base_service import BaseService
from .service_factory import ServiceFactory, ServiceType
from ..models.document import (
    DocumentMessage,
    DocumentMetadata,
    DocumentContent,
    DocumentType
)


class PDFService(BaseService):
    """Service for PDF processing and conversion"""

    def __init__(self):
        """Initialize PDF service"""
        super().__init__("PDFService")
        self.supported_formats = [".pdf"]
        self.logger.info("Initialized PDFService")

    async def pdf_to_markdown(self, file_path: str) -> str:
        """Convert PDF to markdown format

        Args:
            file_path: Path to the PDF file

        Returns:
            Markdown formatted text

        Raises:
            FileNotFoundError: If PDF file doesn't exist
            ValueError: If file is not a PDF
        """
        with self.traced_operation("pdf_to_markdown", file_path=file_path):
            try:
                # Validate file exists and is PDF
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"PDF file not found: {file_path}")

                if not file_path.lower().endswith(".pdf"):
                    raise ValueError(f"File is not a PDF: {file_path}")

                # Use asyncio.to_thread for CPU-intensive PDF processing
                markdown = await asyncio.to_thread(self._sync_pdf_to_markdown, file_path)

                self.logger.info(f"Converted PDF to markdown: {file_path}")
                return markdown

            except Exception as e:
                self.logger.error(f"Failed to convert PDF to markdown: {str(e)}")
                raise

    def _sync_pdf_to_markdown(self, file_path: str) -> str:
        """Synchronous PDF to markdown conversion (CPU-intensive)

        Args:
            file_path: Path to the PDF file

        Returns:
            Markdown formatted text
        """
        try:
            import fitz  # PyMuPDF

            markdown_lines = []
            doc = fitz.open(file_path)

            for page_num, page in enumerate(doc, 1):
                # Add page header
                markdown_lines.append(f"## Page {page_num}\n")

                # Extract text
                text = page.get_text()
                if text.strip():
                    # Clean and format text
                    lines = text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line:
                            # Check if line looks like a heading
                            if line.isupper() and len(line) < 100:
                                markdown_lines.append(f"### {line}\n")
                            else:
                                markdown_lines.append(f"{line}\n")

                    markdown_lines.append("\n")

                # Extract tables if present
                tables = page.find_tables()
                if tables:
                    for table_idx, table in enumerate(tables):
                        markdown_lines.append(f"#### Table {table_idx + 1}\n")
                        markdown_lines.append(self._table_to_markdown(table.extract()))
                        markdown_lines.append("\n")

                markdown_lines.append("---\n\n")

            doc.close()
            return "".join(markdown_lines)

        except ImportError:
            # Fallback if PyMuPDF is not available
            self.logger.warning("PyMuPDF not available, using basic text extraction")
            return self._basic_pdf_extract(file_path)

    def _table_to_markdown(self, table_data: List[List[str]]) -> str:
        """Convert table data to markdown format

        Args:
            table_data: 2D list of table cells

        Returns:
            Markdown formatted table
        """
        if not table_data:
            return ""

        markdown = []

        # Header row
        header = table_data[0] if table_data else []
        if header:
            markdown.append("| " + " | ".join(str(cell or "") for cell in header) + " |")
            markdown.append("| " + " | ".join("---" for _ in header) + " |")

        # Data rows
        for row in table_data[1:]:
            markdown.append("| " + " | ".join(str(cell or "") for cell in row) + " |")

        return "\n".join(markdown) + "\n"

    def _basic_pdf_extract(self, file_path: str) -> str:
        """Basic PDF text extraction fallback

        Args:
            file_path: Path to the PDF file

        Returns:
            Extracted text
        """
        # This is a placeholder for basic extraction
        # In production, would use a library like pypdf2 or pdfplumber
        return f"# PDF Content\n\nBasic extraction from: {file_path}\n\n[PDF extraction requires PyMuPDF library]"

    async def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from PDF file

        Args:
            file_path: Path to the PDF file

        Returns:
            Dictionary containing PDF metadata
        """
        with self.traced_operation("extract_metadata", file_path=file_path):
            try:
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"PDF file not found: {file_path}")

                # Use thread pool for I/O
                metadata = await asyncio.to_thread(self._sync_extract_metadata, file_path)

                self.logger.info(f"Extracted metadata from: {file_path}")
                return metadata

            except Exception as e:
                self.logger.error(f"Failed to extract metadata: {str(e)}")
                raise

    def _sync_extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Synchronous metadata extraction

        Args:
            file_path: Path to the PDF file

        Returns:
            Dictionary containing PDF metadata
        """
        metadata = {
            "file_path": file_path,
            "file_size": os.path.getsize(file_path),
            "file_name": os.path.basename(file_path)
        }

        try:
            import fitz

            doc = fitz.open(file_path)
            metadata.update({
                "page_count": doc.page_count,
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "subject": doc.metadata.get("subject", ""),
                "keywords": doc.metadata.get("keywords", ""),
                "creator": doc.metadata.get("creator", ""),
                "producer": doc.metadata.get("producer", ""),
                "creation_date": doc.metadata.get("creationDate", ""),
                "modification_date": doc.metadata.get("modDate", ""),
                "is_encrypted": doc.is_encrypted,
                "is_form": doc.is_form_pdf
            })
            doc.close()

        except ImportError:
            self.logger.warning("PyMuPDF not available for metadata extraction")

        return metadata

    async def extract_tables(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract tables from PDF file

        Args:
            file_path: Path to the PDF file

        Returns:
            List of tables with their data
        """
        with self.traced_operation("extract_tables", file_path=file_path):
            try:
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"PDF file not found: {file_path}")

                # Use thread pool for CPU-intensive work
                tables = await asyncio.to_thread(self._sync_extract_tables, file_path)

                self.logger.info(f"Extracted {len(tables)} tables from: {file_path}")
                return tables

            except Exception as e:
                self.logger.error(f"Failed to extract tables: {str(e)}")
                raise

    def _sync_extract_tables(self, file_path: str) -> List[Dict[str, Any]]:
        """Synchronous table extraction

        Args:
            file_path: Path to the PDF file

        Returns:
            List of tables with their data
        """
        tables = []

        try:
            import fitz

            doc = fitz.open(file_path)

            for page_num, page in enumerate(doc, 1):
                page_tables = page.find_tables()
                for table_idx, table in enumerate(page_tables):
                    tables.append({
                        "page": page_num,
                        "table_index": table_idx,
                        "data": table.extract(),
                        "rows": len(table.extract()),
                        "columns": len(table.extract()[0]) if table.extract() else 0
                    })

            doc.close()

        except ImportError:
            self.logger.warning("PyMuPDF not available for table extraction")

        return tables

    async def process_pdf_document(
        self,
        file_path: str,
        user_id: str
    ) -> DocumentMessage:
        """Process a PDF file into a DocumentMessage

        Args:
            file_path: Path to the PDF file
            user_id: ID of the user processing the document

        Returns:
            Processed document message
        """
        with self.traced_operation(
            "process_pdf_document",
            file_path=file_path,
            user_id=user_id
        ):
            try:
                # Extract metadata
                metadata_dict = await self.extract_metadata(file_path)

                # Convert to markdown
                markdown_content = await self.pdf_to_markdown(file_path)

                # Extract tables
                tables = await self.extract_tables(file_path)

                # Create document metadata
                metadata = DocumentMetadata(
                    document_type=DocumentType.PDF,
                    name=metadata_dict.get("file_name", "Untitled PDF"),
                    summary=f"PDF document with {metadata_dict.get('page_count', 0)} pages",
                    created_user=user_id,
                    updated_user=user_id,
                    file_size=metadata_dict.get("file_size", 0),
                    mime_type="application/pdf",
                    tags=["pdf", "processed"]
                )

                # Create document content
                content = DocumentContent(
                    formatted_content=markdown_content,
                    raw_text=markdown_content,  # For now, same as formatted
                    structured_data={
                        "metadata": metadata_dict,
                        "tables": tables,
                        "page_count": metadata_dict.get("page_count", 0)
                    }
                )

                # Create document message
                document = DocumentMessage(
                    metadata=metadata,
                    content=content,
                    tools=["pdf_reader", "table_extractor"],
                    user_id=user_id
                )

                self.logger.info(f"Processed PDF document: {file_path}")
                return document

            except Exception as e:
                self.logger.error(f"Failed to process PDF document: {str(e)}")
                raise

    async def extract_images(self, file_path: str, output_dir: Optional[str] = None) -> List[str]:
        """Extract images from PDF file

        Args:
            file_path: Path to the PDF file
            output_dir: Directory to save extracted images (uses temp dir if not provided)

        Returns:
            List of paths to extracted images
        """
        with self.traced_operation(
            "extract_images",
            file_path=file_path,
            output_dir=output_dir
        ):
            try:
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"PDF file not found: {file_path}")

                # Use temp directory if not provided
                if output_dir is None:
                    output_dir = tempfile.mkdtemp(prefix="pdf_images_")

                # Use thread pool for I/O
                image_paths = await asyncio.to_thread(
                    self._sync_extract_images,
                    file_path,
                    output_dir
                )

                self.logger.info(f"Extracted {len(image_paths)} images from: {file_path}")
                return image_paths

            except Exception as e:
                self.logger.error(f"Failed to extract images: {str(e)}")
                raise

    def _sync_extract_images(self, file_path: str, output_dir: str) -> List[str]:
        """Synchronous image extraction

        Args:
            file_path: Path to the PDF file
            output_dir: Directory to save images

        Returns:
            List of extracted image paths
        """
        image_paths = []

        try:
            import fitz

            doc = fitz.open(file_path)

            for page_num, page in enumerate(doc):
                image_list = page.get_images()

                for img_idx, img in enumerate(image_list):
                    xref = img[0]
                    image = doc.extract_image(xref)
                    image_bytes = image["image"]
                    image_ext = image["ext"]

                    # Save image
                    image_filename = f"page{page_num + 1}_img{img_idx + 1}.{image_ext}"
                    image_path = os.path.join(output_dir, image_filename)

                    with open(image_path, "wb") as f:
                        f.write(image_bytes)

                    image_paths.append(image_path)

            doc.close()

        except ImportError:
            self.logger.warning("PyMuPDF not available for image extraction")

        return image_paths

    async def health_check(self) -> Dict[str, Any]:
        """Check service health

        Returns:
            Health status dictionary
        """
        with self.traced_operation("health_check"):
            try:
                # Check if PyMuPDF is available
                try:
                    import fitz
                    pymupdf_available = True
                    pymupdf_version = fitz.version[0]
                except ImportError:
                    pymupdf_available = False
                    pymupdf_version = None

                health_status = {
                    "service": "PDFService",
                    "status": "healthy" if pymupdf_available else "degraded",
                    "dependencies": {
                        "PyMuPDF": {
                            "available": pymupdf_available,
                            "version": pymupdf_version
                        }
                    },
                    "supported_formats": self.supported_formats,
                    "timestamp": datetime.utcnow().isoformat()
                }

                self.logger.info(f"Health check: {health_status['status']}")
                return health_status

            except Exception as e:
                self.logger.error(f"Health check failed: {str(e)}")
                return {
                    "service": "PDFService",
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }


# Register with factory
ServiceFactory.register(ServiceType.PDF, PDFService)