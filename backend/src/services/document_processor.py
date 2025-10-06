"""Document processor that orchestrates document processing using existing services"""

import asyncio
from typing import Optional, Callable, Dict, Any
from pathlib import Path
from datetime import datetime

from .base_service import BaseService
from .service_factory import ServiceFactory, ServiceType
from ..models.document import DocumentMessage, DocumentType, ProcessingStage
from ..storage.storage_factory import StorageFactory, StorageType
import aiofiles


class DocumentProcessor(BaseService):
    """Orchestrates document processing using existing services

    This service follows the existing pattern and uses ServiceFactory
    to get the appropriate services for each document type.
    """

    def __init__(self):
        """Initialize document processor with required services"""
        super().__init__("DocumentProcessor")

        # Use ServiceFactory to get services (following existing pattern)
        self.pdf_service = None
        self.llm_service = None
        self.transcription_service = None
        self.web_scraping_service = None

        # Document type to file extension mapping
        self.extension_map = {
            '.pdf': DocumentType.PDF,
            '.txt': DocumentType.MARKDOWN,
            '.md': DocumentType.MARKDOWN,
            '.json': DocumentType.JSON,
            '.xml': DocumentType.XML,
            '.csv': DocumentType.CSV,
            '.xls': DocumentType.EXCEL,
            '.xlsx': DocumentType.EXCEL,
            '.doc': DocumentType.WORD,
            '.docx': DocumentType.WORD,
            '.mp3': DocumentType.PODCAST,
            '.mp4': DocumentType.YOUTUBE,
            '.wav': DocumentType.PODCAST,
            '.html': DocumentType.WEBPAGE,
            '.htm': DocumentType.WEBPAGE
        }

    def _ensure_services(self):
        """Lazy load services as needed"""
        if not self.llm_service:
            try:
                self.llm_service = ServiceFactory.create(ServiceType.LLM)
            except Exception as e:
                self.logger.warning(f"LLM service not available: {e}")

    def detect_document_type(self, file_path: str) -> DocumentType:
        """Detect document type from file extension

        Args:
            file_path: Path to the file

        Returns:
            Detected document type
        """
        file_extension = Path(file_path).suffix.lower()
        return self.extension_map.get(file_extension, DocumentType.MARKDOWN)

    async def process_document(
        self,
        file_path: str,
        document: DocumentMessage,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> DocumentMessage:
        """Process document based on its type

        This method orchestrates the processing using existing services,
        following the established service pattern.

        Args:
            file_path: Path to the document file
            document: Document message to process
            progress_callback: Optional callback for progress updates

        Returns:
            Processed document with content and metadata
        """
        with self.traced_operation("process_document",
                                  document_id=document.metadata.document_id,
                                  file_path=file_path):
            try:
                # Detect document type
                doc_type = self.detect_document_type(file_path)
                document.metadata.document_type = doc_type

                if progress_callback:
                    await progress_callback(10, f"Processing {doc_type.value} document")

                # Process based on document type using existing services
                if doc_type == DocumentType.PDF:
                    await self._process_pdf(file_path, document, progress_callback)
                elif doc_type in [DocumentType.YOUTUBE, DocumentType.PODCAST]:
                    await self._process_media(file_path, document, doc_type, progress_callback)
                elif doc_type == DocumentType.WEBPAGE:
                    await self._process_webpage(file_path, document, progress_callback)
                elif doc_type in [DocumentType.WORD, DocumentType.MARKDOWN]:
                    await self._process_text_document(file_path, document, progress_callback)
                elif doc_type == DocumentType.JSON:
                    await self._process_json(file_path, document, progress_callback)
                elif doc_type == DocumentType.XML:
                    await self._process_xml(file_path, document, progress_callback)
                elif doc_type in [DocumentType.EXCEL, DocumentType.CSV]:
                    await self._process_spreadsheet(file_path, document, doc_type, progress_callback)
                else:
                    # Default text processing
                    await self._process_text_document(file_path, document, progress_callback)

                # Generate metadata (summary and language detection)
                if progress_callback:
                    await progress_callback(70, "Generating metadata")

                self.logger.info(f"[DOC-PROCESS] Starting metadata generation for {document.metadata.document_id}")
                await self._generate_metadata(document)
                self.logger.info(f"[DOC-PROCESS] Metadata generation complete for {document.metadata.document_id}")
                self.logger.info(f"[DOC-PROCESS] Final summary: {document.metadata.summary[:200] if document.metadata.summary else 'NO SUMMARY'}...")

                if progress_callback:
                    await progress_callback(100, "Processing complete")

                # Set processing stage to completed
                # Note: updated_timestamp is automatically updated when document is saved
                document.metadata.processing_stage = ProcessingStage.COMPLETED

                return document

            except Exception as e:
                self.logger.error(f"Document processing failed: {e}", exc_info=True)
                document.metadata.processing_stage = ProcessingStage.FAILED
                # Note: last_error field doesn't exist in DocumentMetadata
                # The error is already logged above
                raise

    async def _process_pdf(
        self,
        file_path: str,
        document: DocumentMessage,
        progress_callback: Optional[Callable] = None
    ):
        """Process PDF using PDFService"""
        doc_id = document.metadata.document_id
        self.logger.info(f"[PDF-PROCESS] Starting PDF processing for {doc_id}: {file_path}")

        if not self.pdf_service:
            self.pdf_service = ServiceFactory.create(ServiceType.PDF)

        if progress_callback:
            await progress_callback(30, "Converting PDF to markdown")

        # Use existing PDFService method
        self.logger.info(f"[PDF-PROCESS] Converting PDF to markdown for {doc_id}")
        markdown_content = await self.pdf_service.pdf_to_markdown(file_path)

        content_length = len(markdown_content)
        first_100_chars = markdown_content[:100] if markdown_content else "EMPTY"
        self.logger.info(f"[PDF-PROCESS] PDF converted for {doc_id}: {content_length} characters")
        self.logger.info(f"[PDF-PROCESS] First 100 chars: {first_100_chars}...")

        document.content.formatted_content = markdown_content
        document.content.raw_text = markdown_content
        self.logger.info(f"[PDF-PROCESS] Content saved to document {doc_id}")

        if progress_callback:
            await progress_callback(60, "PDF conversion complete")

    async def _process_text_document(
        self,
        file_path: str,
        document: DocumentMessage,
        progress_callback: Optional[Callable] = None
    ):
        """Process text-based documents"""
        if progress_callback:
            await progress_callback(30, "Reading text content")

        # Read file content
        async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            raw_text = await f.read()

        document.content.raw_text = raw_text

        # Try to convert to markdown if LLM is available
        self._ensure_services()
        if self.llm_service:
            if progress_callback:
                await progress_callback(40, "Formatting content")

            try:
                formatted_content = await asyncio.wait_for(
                    self.llm_service.text_to_markdown(raw_text[:10000]),
                    timeout=30.0
                )
                document.content.formatted_content = formatted_content
            except (asyncio.TimeoutError, Exception) as e:
                self.logger.warning(f"Markdown formatting failed: {e}, using raw text")
                document.content.formatted_content = raw_text
        else:
            document.content.formatted_content = raw_text

        if progress_callback:
            await progress_callback(60, "Text processing complete")

    async def _process_media(
        self,
        file_path: str,
        document: DocumentMessage,
        doc_type: DocumentType,
        progress_callback: Optional[Callable] = None
    ):
        """Process media files using TranscriptionService"""
        if not self.transcription_service:
            self.transcription_service = ServiceFactory.create(ServiceType.TRANSCRIPTION)

        if progress_callback:
            await progress_callback(30, "Transcribing media")

        # For YouTube, file_path contains the URL
        if doc_type == DocumentType.YOUTUBE:
            transcript = await self.transcription_service.transcribe_youtube(file_path)
        else:
            # For podcasts, transcribe the audio file
            transcript = await self.transcription_service.transcribe_podcast(file_path)

        document.content.raw_text = transcript
        document.content.formatted_content = transcript

        if progress_callback:
            await progress_callback(60, "Transcription complete")

    async def _process_webpage(
        self,
        file_path: str,
        document: DocumentMessage,
        progress_callback: Optional[Callable] = None
    ):
        """Process webpage using WebScrapingService"""
        if not self.web_scraping_service:
            self.web_scraping_service = ServiceFactory.create(ServiceType.WEB_SCRAPING)

        if progress_callback:
            await progress_callback(30, "Scraping webpage")

        # For webpages, file_path contains the URL
        markdown_content = await self.web_scraping_service.scrape_to_markdown(file_path)

        document.content.raw_text = markdown_content
        document.content.formatted_content = markdown_content

        if progress_callback:
            await progress_callback(60, "Web scraping complete")

    async def _process_json(
        self,
        file_path: str,
        document: DocumentMessage,
        progress_callback: Optional[Callable] = None
    ):
        """Process JSON files"""
        if progress_callback:
            await progress_callback(30, "Processing JSON")

        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()

        # Pretty print JSON for readability
        import json
        try:
            data = json.loads(content)
            formatted = json.dumps(data, indent=2, ensure_ascii=False)
            document.content.formatted_content = f"```json\n{formatted}\n```"
            document.content.raw_text = content
        except json.JSONDecodeError:
            document.content.formatted_content = content
            document.content.raw_text = content

        if progress_callback:
            await progress_callback(60, "JSON processing complete")

    async def _process_xml(
        self,
        file_path: str,
        document: DocumentMessage,
        progress_callback: Optional[Callable] = None
    ):
        """Process XML files"""
        if progress_callback:
            await progress_callback(30, "Processing XML")

        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()

        # Format XML for readability
        document.content.formatted_content = f"```xml\n{content}\n```"
        document.content.raw_text = content

        if progress_callback:
            await progress_callback(60, "XML processing complete")

    async def _process_spreadsheet(
        self,
        file_path: str,
        document: DocumentMessage,
        doc_type: DocumentType,
        progress_callback: Optional[Callable] = None
    ):
        """Process spreadsheet files (Excel, CSV)"""
        if progress_callback:
            await progress_callback(30, "Processing spreadsheet")

        # For now, read as text
        # TODO: Implement proper Excel/CSV processing
        try:
            if doc_type == DocumentType.CSV:
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                document.content.raw_text = content
                document.content.formatted_content = f"```csv\n{content}\n```"
            else:
                # Excel files need special handling
                document.content.raw_text = "Excel file processing not yet implemented"
                document.content.formatted_content = "Excel file processing not yet implemented"
        except Exception as e:
            self.logger.warning(f"Spreadsheet processing failed: {e}")
            document.content.raw_text = str(e)
            document.content.formatted_content = str(e)

        if progress_callback:
            await progress_callback(60, "Spreadsheet processing complete")

    async def _generate_metadata(self, document: DocumentMessage):
        """Generate summary and detect language"""
        doc_id = document.metadata.document_id
        self.logger.info(f"[SUMMARY-GEN] Starting metadata generation for document {doc_id}")
        self._ensure_services()

        if not self.llm_service:
            # Fallback if LLM is not available
            self.logger.warning(f"[SUMMARY-GEN] No LLM service available for {doc_id}, using fallback")
            document.metadata.language = "en"
            fallback_summary = self._generate_fallback_summary(document.content.raw_text)
            document.metadata.summary = fallback_summary
            self.logger.info(f"[SUMMARY-GEN] Fallback summary for {doc_id}: {fallback_summary[:100]}...")
            return

        raw_text = document.content.raw_text or ""
        text_length = len(raw_text)
        self.logger.info(f"[SUMMARY-GEN] Document {doc_id} has {text_length} characters of raw text")

        try:
            # Detect language
            self.logger.info(f"[SUMMARY-GEN] Detecting language for {doc_id}...")
            language_result = await asyncio.wait_for(
                self.llm_service.detect_language(raw_text[:1000]),
                timeout=10.0
            )
            document.metadata.language = language_result[0] if language_result else "en"
            self.logger.info(f"[SUMMARY-GEN] Detected language for {doc_id}: {document.metadata.language}")

            # Generate summary
            summary_input = raw_text[:3000]
            self.logger.info(f"[SUMMARY-GEN] Generating AI summary for {doc_id} using {len(summary_input)} characters...")
            summary = await asyncio.wait_for(
                self.llm_service.generate_summary(
                    summary_input,
                    max_length=100,
                    style="concise"
                ),
                timeout=20.0
            )
            document.metadata.summary = summary
            self.logger.info(f"[SUMMARY-GEN] AI summary generated for {doc_id}: {summary[:150]}...")

        except Exception as e:
            self.logger.error(f"[SUMMARY-GEN] Metadata generation failed for {doc_id}: {e}", exc_info=True)
            document.metadata.language = "en"
            fallback_summary = self._generate_fallback_summary(raw_text)
            document.metadata.summary = fallback_summary
            self.logger.info(f"[SUMMARY-GEN] Using fallback summary for {doc_id}: {fallback_summary[:100]}...")

    def _generate_fallback_summary(self, text: str) -> str:
        """Generate a simple fallback summary"""
        if not text:
            return "Empty document"

        lines = text.split('\n')
        non_empty_lines = [line.strip() for line in lines if line.strip()][:3]
        summary = ' '.join(non_empty_lines)[:100]

        return summary if summary else "Document with no extractable text"

    async def health_check(self) -> Dict[str, Any]:
        """Check health of document processor"""
        return {
            "service": "DocumentProcessor",
            "status": "healthy",
            "services_available": {
                "pdf": self.pdf_service is not None,
                "llm": self.llm_service is not None,
                "transcription": self.transcription_service is not None,
                "web_scraping": self.web_scraping_service is not None
            }
        }


# Register with ServiceFactory
from .service_factory import ServiceFactory, ServiceType
ServiceFactory.register(ServiceType.DOCUMENT_PROCESSOR, DocumentProcessor)


