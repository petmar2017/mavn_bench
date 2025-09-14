"""PDF processing service with markdown conversion"""

import asyncio
import os
import base64
from typing import Dict, List, Optional, Any
from pathlib import Path
import tempfile
from datetime import datetime

from .base_service import BaseService
from .service_factory import ServiceFactory, ServiceType
from .llm_service import LLMService, LLMProvider
from ..models.document import (
    DocumentMessage,
    DocumentMetadata,
    DocumentContent,
    DocumentType
)
from ..core.config import get_settings


class PDFService(BaseService):
    """Service for PDF processing and conversion"""

    def __init__(self, use_ai: bool = True, prefer_pymupdf: bool = True):
        """Initialize PDF service

        Args:
            use_ai: Whether to use Claude AI for PDF conversion
            prefer_pymupdf: Whether to prefer PyMuPDF over AI when both are available
        """
        super().__init__("PDFService")
        self.supported_formats = [".pdf"]
        self.use_ai = use_ai
        self.prefer_pymupdf = prefer_pymupdf

        # Check which PDF libraries are available
        self.has_pymupdf = self._check_pymupdf()
        self.has_pypdf2 = self._check_pypdf2()

        # Initialize LLM service for AI-powered PDF conversion
        self.llm_service = None
        settings = get_settings()
        if use_ai and settings.llm.anthropic_api_key:
            self.llm_service = LLMService(provider=LLMProvider.ANTHROPIC)
            self.logger.info(f"Initialized PDFService with Claude AI (PyMuPDF: {self.has_pymupdf}, PyPDF2: {self.has_pypdf2})")
        else:
            self.logger.info(f"Initialized PDFService with traditional conversion (PyMuPDF: {self.has_pymupdf}, PyPDF2: {self.has_pypdf2})")

    def _check_pymupdf(self) -> bool:
        """Check if PyMuPDF is available"""
        try:
            import fitz
            return True
        except ImportError:
            return False

    def _check_pypdf2(self) -> bool:
        """Check if PyPDF2 is available"""
        try:
            import PyPDF2
            return True
        except ImportError:
            return False

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

                # Decide which method to use based on availability and preferences
                if self.prefer_pymupdf and self.has_pymupdf:
                    # Prefer PyMuPDF if available and preferred
                    markdown = await asyncio.to_thread(self._sync_pdf_to_markdown, file_path)
                    self.logger.info("Using PyMuPDF for PDF conversion")
                elif self.use_ai and self.llm_service and (self.has_pymupdf or self.has_pypdf2):
                    # Use Claude AI if we can extract basic text first
                    markdown = await self._ai_pdf_to_markdown(file_path)
                    self.logger.info("Using Claude AI for PDF conversion")
                elif self.has_pymupdf:
                    # Fall back to PyMuPDF if available
                    markdown = await asyncio.to_thread(self._sync_pdf_to_markdown, file_path)
                    self.logger.info("Using PyMuPDF for PDF conversion (fallback)")
                elif self.has_pypdf2:
                    # Last resort: use PyPDF2
                    markdown = await asyncio.to_thread(self._basic_pdf_extract, file_path)
                    self.logger.info("Using PyPDF2 for PDF conversion (fallback)")
                else:
                    # No PDF library available
                    raise RuntimeError("No PDF processing library available. Install PyMuPDF or PyPDF2.")

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

    async def _ai_pdf_to_markdown(self, file_path: str, use_vision: bool = False) -> str:
        """Convert PDF to markdown using Claude AI

        Args:
            file_path: Path to the PDF file
            use_vision: Whether to use Claude's vision API for better accuracy

        Returns:
            Markdown formatted text from Claude AI
        """
        try:
            if use_vision:
                # Use vision API for better accuracy (especially with complex layouts)
                return await self._ai_pdf_vision_to_markdown(file_path)

            # First extract text using traditional method for context
            basic_text = await asyncio.to_thread(self._sync_pdf_to_markdown, file_path)

            # Create a prompt for Claude to enhance and format the PDF content
            prompt = f"""Convert the following PDF text content into well-formatted Markdown.
Please:
1. Identify and properly format headings (use #, ##, ###)
2. Format lists and bullet points correctly
3. Preserve table structures using Markdown tables
4. Clean up any OCR errors or formatting issues
5. Add appropriate line breaks and spacing
6. Identify and format code blocks if present
7. Keep all important information but improve readability

PDF Content:
{basic_text[:8000]}  # Limit to avoid token limits

Output the improved Markdown content:"""

            # Use Claude to enhance the markdown (uses provider's default settings)
            enhanced_markdown = await self.llm_service._call_llm(prompt)

            self.logger.info("Successfully converted PDF using Claude AI")
            return enhanced_markdown

        except Exception as e:
            self.logger.warning(f"AI conversion failed, falling back to traditional: {str(e)}")
            # Fall back to traditional conversion
            return await asyncio.to_thread(self._sync_pdf_to_markdown, file_path)

    async def _ai_pdf_vision_to_markdown(self, file_path: str) -> str:
        """Convert PDF to markdown using Claude's vision API

        Args:
            file_path: Path to the PDF file

        Returns:
            Markdown formatted text from Claude Vision API
        """
        try:
            import fitz  # PyMuPDF
            from PIL import Image
            import io

            # Convert PDF pages to images
            doc = fitz.open(file_path)
            markdown_parts = []

            for page_num, page in enumerate(doc, 1):
                # Convert page to image
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x scale for better quality
                img_data = pix.tobytes("png")

                # Convert to base64 for Claude Vision API
                img_base64 = base64.b64encode(img_data).decode('utf-8')

                # Create prompt for vision API
                vision_prompt = f"""You are looking at page {page_num} of a PDF document.
Please convert this page to well-formatted Markdown.
Include:
- All text content
- Proper heading hierarchy
- Tables in Markdown format
- Lists and bullet points
- Code blocks if present
- Image descriptions where relevant

Output only the Markdown content for this page:"""

                # Note: This would require updating the LLM service to support vision API
                # For now, we'll use the text-based approach
                self.logger.info(f"Processing page {page_num} with vision API")

                # Placeholder for vision API call
                # page_markdown = await self.llm_service._call_vision_api(img_base64, vision_prompt)
                # markdown_parts.append(f"## Page {page_num}\n\n{page_markdown}\n")

            doc.close()
            return "\n".join(markdown_parts)

        except Exception as e:
            self.logger.error(f"Vision API conversion failed: {str(e)}")
            # Fall back to text-based AI conversion
            return await self._ai_pdf_to_markdown(file_path, use_vision=False)

    def _basic_pdf_extract(self, file_path: str) -> str:
        """Basic PDF text extraction fallback using PyPDF2

        Args:
            file_path: Path to the PDF file

        Returns:
            Extracted text
        """
        try:
            # Try using PyPDF2 as a fallback
            from PyPDF2 import PdfReader

            reader = PdfReader(file_path)
            text_content = []

            for page_num, page in enumerate(reader.pages, 1):
                text_content.append(f"## Page {page_num}\n")
                page_text = page.extract_text()
                if page_text:
                    # Clean up the text a bit
                    lines = page_text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line:
                            text_content.append(line)
                    text_content.append("")  # Add blank line between pages

            extracted_text = "\n".join(text_content)

            if extracted_text.strip():
                self.logger.info("Successfully extracted PDF text using PyPDF2 fallback")
                return extracted_text
            else:
                self.logger.warning("PyPDF2 extracted no text from PDF")
                return "# PDF Content\n\nNo text content could be extracted from this PDF file."

        except Exception as e:
            self.logger.error(f"PyPDF2 extraction failed: {str(e)}")
            # Last resort fallback
            return f"# PDF Content\n\nFailed to extract content from PDF: {str(e)}"

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

                # Detect language and generate summary if LLM service is available
                language = "en"  # Default
                summary = None
                if self.llm_service:
                    try:
                        # Detect language
                        lang_result = await self.llm_service.detect_language(markdown_content[:1000])
                        language = lang_result[0] if lang_result[0] != "unknown" else "en"

                        # Generate summary
                        summary = await self.llm_service.generate_summary(
                            markdown_content[:3000],  # Use first 3000 chars for summary
                            max_length=100,
                            style="concise"
                        )
                    except Exception as e:
                        self.logger.warning(f"Failed to detect language or generate summary: {str(e)}")

                # Extract tables
                tables = await self.extract_tables(file_path)

                # Create document metadata
                metadata = DocumentMetadata(
                    document_type=DocumentType.PDF,
                    name=metadata_dict.get("file_name", "Untitled PDF"),
                    summary=summary or f"PDF document with {metadata_dict.get('page_count', 0)} pages",
                    language=language,
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

    async def validate_and_extract_pdf(
        self,
        file_path: str,
        extracted_text: str
    ) -> Dict[str, Any]:
        """Validate PDF extraction quality and re-extract if needed using LLM

        Args:
            file_path: Path to the PDF file
            extracted_text: Previously extracted text to validate

        Returns:
            Dict with validation result and improved extraction if needed
        """
        with self.traced_operation(
            "validate_and_extract_pdf",
            file_path=file_path
        ):
            try:
                # Check if we have LLM service available
                if not self.llm_service:
                    self.logger.warning("No LLM service available for PDF validation")
                    return {
                        "quality_assessment": "unknown",
                        "needs_reprocessing": False,
                        "improved_extraction": extracted_text,
                        "validation_notes": "LLM service not available"
                    }

                # Create validation prompt
                validation_prompt = f"""You have been provided with a PDF document and its extracted text.

Please evaluate the quality of the text extraction and perform the following tasks:

1. Check if the extracted text is meaningful and complete (not just "---" or placeholder text)
2. If the extraction is poor quality, extract the text properly from the PDF
3. Convert the content to clean, well-formatted Markdown

Current extracted text preview (first 500 chars):
{extracted_text[:500] if extracted_text else "(empty)"}

Please respond with:
- Quality Assessment: (Good/Poor)
- If Poor, provide the properly extracted and formatted Markdown content from the PDF
- Ensure all text, tables, and structure are preserved

Format the response as clean Markdown suitable for display."""

                # Call LLM with PDF attachment using the internal method
                response = await self.llm_service._call_llm_with_file(
                    prompt=validation_prompt,
                    file_path=file_path,
                    max_tokens=4000  # Allow more tokens for full extraction
                )

                # Parse response to determine if we need to use the LLM's extraction
                is_poor_quality = "poor" in response.lower()[:100] or "---" in extracted_text[:100]

                return {
                    "quality_assessment": "poor" if is_poor_quality else "good",
                    "needs_reprocessing": is_poor_quality,
                    "improved_extraction": response if is_poor_quality else extracted_text,
                    "validation_notes": response[:200] if not is_poor_quality else None
                }

            except Exception as e:
                self.logger.error(f"PDF validation failed: {str(e)}")
                # Return original text if validation fails
                return {
                    "quality_assessment": "unknown",
                    "needs_reprocessing": False,
                    "improved_extraction": extracted_text,
                    "validation_notes": f"Validation failed: {str(e)}"
                }

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


# Register with factory using configuration
def create_pdf_service():
    """Factory function to create PDFService with configuration settings"""
    from src.core.config import get_settings
    settings = get_settings()
    return PDFService(
        use_ai=settings.llm.pdf_use_ai,
        prefer_pymupdf=settings.llm.pdf_prefer_pymupdf
    )

ServiceFactory.register(ServiceType.PDF, create_pdf_service)