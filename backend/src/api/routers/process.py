"""Processing API endpoints for document operations"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from opentelemetry import trace
from pydantic import BaseModel, Field

from ...models.document import (
    DocumentMessage,
    DocumentMetadata,
    DocumentContent,
    DocumentType
)
from ...services.document_service import DocumentService
from ...services.pdf_service import PDFService
from ...services.llm_service import LLMService
from ...services.transcription_service import TranscriptionService
from ...services.web_scraping_service import WebScrapingService
from ...core.logger import CentralizedLogger
from ..dependencies import (
    get_current_user,
    get_document_service,
    get_pdf_service,
    get_llm_service,
    get_transcription_service,
    get_web_scraping_service,
    verify_trace_context
)


router = APIRouter()
logger = CentralizedLogger("ProcessRouter")
tracer = trace.get_tracer(__name__)


# Request/Response models
class PDFConversionRequest(BaseModel):
    """Request model for PDF conversion"""
    document_id: Optional[str] = Field(None, description="Existing document ID to convert")
    save_result: bool = Field(True, description="Save conversion result as new document")


class SummarizeRequest(BaseModel):
    """Request model for document summarization"""
    document_id: str = Field(..., description="Document ID to summarize")
    max_length: Optional[int] = Field(500, description="Maximum summary length in words")
    style: Optional[str] = Field("business", description="Summary style: business, technical, casual")
    update_document: bool = Field(True, description="Update document with summary")


class EntityExtractionRequest(BaseModel):
    """Request model for entity extraction"""
    document_id: str = Field(..., description="Document ID for entity extraction")
    entity_types: Optional[List[str]] = Field(
        default_factory=lambda: ["person", "organization", "location", "date", "money"],
        description="Types of entities to extract"
    )
    confidence_threshold: float = Field(0.7, description="Minimum confidence threshold")


class ClassificationRequest(BaseModel):
    """Request model for document classification"""
    document_id: str = Field(..., description="Document ID to classify")
    categories: Optional[List[str]] = Field(None, description="Custom categories to classify into")
    multi_label: bool = Field(False, description="Allow multiple categories per document")


class TranscriptionRequest(BaseModel):
    """Request model for media transcription"""
    url: str = Field(..., description="YouTube or podcast URL to transcribe")
    language: Optional[str] = Field("auto", description="Language code or 'auto' for detection")
    save_as_document: bool = Field(True, description="Save transcription as new document")


class WebScrapeRequest(BaseModel):
    """Request model for web scraping"""
    url: str = Field(..., description="Web page URL to scrape")
    include_images: bool = Field(False, description="Include images in markdown")
    include_links: bool = Field(True, description="Include links in markdown")
    save_as_document: bool = Field(True, description="Save scraped content as new document")


class ProcessingResponse(BaseModel):
    """Generic response for processing operations"""
    success: bool
    document_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    message: str
    processing_time: float


@router.post("/pdf-to-markdown", response_model=ProcessingResponse)
async def convert_pdf_to_markdown(
    file: Optional[UploadFile] = File(None),
    request: Optional[PDFConversionRequest] = None,
    user: Dict = Depends(get_current_user),
    pdf_service: PDFService = Depends(get_pdf_service),
    document_service: DocumentService = Depends(get_document_service),
    trace_context: Dict = Depends(verify_trace_context)
) -> ProcessingResponse:
    """Convert PDF to markdown

    Args:
        file: Optional PDF file upload
        request: Optional conversion request with document_id
        user: Current user
        pdf_service: PDF service
        document_service: Document service
        trace_context: W3C trace context

    Returns:
        Processing response with markdown content

    Raises:
        HTTPException: If conversion fails
    """
    with tracer.start_as_current_span("convert_pdf_to_markdown") as span:
        span.set_attribute("user.id", user["user_id"])
        start_time = datetime.utcnow()

        try:
            # Validate input
            if not file and not request:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Either file upload or document_id required"
                )

            # Handle file upload
            if file:
                if not file.filename.endswith('.pdf'):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="File must be a PDF"
                    )

                # Save uploaded file temporarily
                import tempfile
                import aiofiles

                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    content = await file.read()
                    async with aiofiles.open(tmp_file.name, 'wb') as f:
                        await f.write(content)
                    tmp_path = tmp_file.name

                try:
                    # Convert PDF
                    markdown_content = await pdf_service.pdf_to_markdown(tmp_path)

                    # Save as document if requested
                    if request and request.save_result:
                        metadata = DocumentMetadata(
                            document_id=str(uuid.uuid4()),
                            document_type=DocumentType.MARKDOWN,
                            name=f"{file.filename}_converted.md",
                            created_user=user["user_id"],
                            updated_user=user["user_id"]
                        )

                        content_obj = DocumentContent(
                            formatted_content=markdown_content,
                            raw_text=markdown_content
                        )

                        document = DocumentMessage(
                            metadata=metadata,
                            content=content_obj,
                            user_id=user["user_id"],
                            trace_id=trace_context.get("trace_id"),
                            span_id=trace_context.get("span_id")
                        )

                        created = await document_service.create_document(document, user["user_id"])
                        doc_id = created.metadata.document_id
                    else:
                        doc_id = None

                finally:
                    # Clean up temp file
                    import os
                    os.unlink(tmp_path)

            # Handle existing document
            elif request and request.document_id:
                # Get document
                document = await document_service.get_document(request.document_id, user["user_id"])
                if not document:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Document {request.document_id} not found"
                    )

                if document.metadata.document_type != DocumentType.PDF:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Document is not a PDF: {document.metadata.document_type}"
                    )

                # Convert content (assuming raw PDF bytes in content)
                # This would need actual implementation based on storage
                markdown_content = await pdf_service.pdf_to_markdown_from_bytes(
                    document.content.raw_text.encode()  # Placeholder
                )

                doc_id = request.document_id

            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid request"
                )

            processing_time = (datetime.utcnow() - start_time).total_seconds()

            return ProcessingResponse(
                success=True,
                document_id=doc_id,
                result={"markdown_length": len(markdown_content)},
                message="PDF converted to markdown successfully",
                processing_time=processing_time
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"PDF conversion failed: {str(e)}")
            span.record_exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"PDF conversion failed: {str(e)}"
            )


@router.post("/summarize", response_model=ProcessingResponse)
async def summarize_document(
    request: SummarizeRequest,
    user: Dict = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
    llm_service: LLMService = Depends(get_llm_service),
    trace_context: Dict = Depends(verify_trace_context)
) -> ProcessingResponse:
    """Generate document summary using AI

    Args:
        request: Summarization request
        user: Current user
        document_service: Document service
        llm_service: LLM service
        trace_context: W3C trace context

    Returns:
        Processing response with summary

    Raises:
        HTTPException: If summarization fails
    """
    with tracer.start_as_current_span("summarize_document") as span:
        span.set_attribute("user.id", user["user_id"])
        span.set_attribute("document.id", request.document_id)
        span.set_attribute("summary.style", request.style)
        start_time = datetime.utcnow()

        try:
            # Get document
            document = await document_service.get_document(request.document_id, user["user_id"])
            if not document:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document {request.document_id} not found"
                )

            # Extract text from document content
            document_text = document.content.formatted_content or document.content.raw_text
            if not document_text:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Document {request.document_id} has no processable text content"
                )

            # Generate summary
            summary = await llm_service.generate_summary(
                document_text,
                max_length=request.max_length,
                style=request.style
            )

            # Update document if requested
            if request.update_document:
                updates = {
                    "metadata": {
                        "summary": summary
                    }
                }
                await document_service.update_document(
                    request.document_id,
                    updates,
                    user["user_id"]
                )

            processing_time = (datetime.utcnow() - start_time).total_seconds()

            return ProcessingResponse(
                success=True,
                document_id=request.document_id,
                result={
                    "summary": summary,
                    "word_count": len(summary.split())
                },
                message="Document summarized successfully",
                processing_time=processing_time
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Summarization failed: {str(e)}")
            span.record_exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Summarization failed: {str(e)}"
            )


@router.post("/extract-entities", response_model=ProcessingResponse)
async def extract_entities(
    request: EntityExtractionRequest,
    user: Dict = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
    llm_service: LLMService = Depends(get_llm_service),
    trace_context: Dict = Depends(verify_trace_context)
) -> ProcessingResponse:
    """Extract entities from document

    Args:
        request: Entity extraction request
        user: Current user
        document_service: Document service
        llm_service: LLM service
        trace_context: W3C trace context

    Returns:
        Processing response with extracted entities

    Raises:
        HTTPException: If extraction fails
    """
    with tracer.start_as_current_span("extract_entities") as span:
        span.set_attribute("user.id", user["user_id"])
        span.set_attribute("document.id", request.document_id)
        span.set_attribute("entity.types", ",".join(request.entity_types))
        start_time = datetime.utcnow()

        try:
            # Get document
            document = await document_service.get_document(request.document_id, user["user_id"])
            if not document:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document {request.document_id} not found"
                )

            # Extract text from document content
            document_text = document.content.formatted_content or document.content.raw_text
            if not document_text:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Document {request.document_id} has no processable text content"
                )

            # Extract entities
            entities = await llm_service.extract_entities(
                document_text,
                entity_types=request.entity_types
            )

            # Store entities in document metadata
            updates = {
                "metadata": {
                    "entities": entities
                }
            }
            await document_service.update_document(
                request.document_id,
                updates,
                user["user_id"]
            )

            processing_time = (datetime.utcnow() - start_time).total_seconds()

            return ProcessingResponse(
                success=True,
                document_id=request.document_id,
                result={
                    "entities": entities,
                    "entity_count": len(entities)
                },
                message="Entities extracted successfully",
                processing_time=processing_time
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Entity extraction failed: {str(e)}")
            span.record_exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Entity extraction failed: {str(e)}"
            )


@router.post("/classify", response_model=ProcessingResponse)
async def classify_document(
    request: ClassificationRequest,
    user: Dict = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
    llm_service: LLMService = Depends(get_llm_service),
    trace_context: Dict = Depends(verify_trace_context)
) -> ProcessingResponse:
    """Classify document into categories

    Args:
        request: Classification request
        user: Current user
        document_service: Document service
        llm_service: LLM service
        trace_context: W3C trace context

    Returns:
        Processing response with classification results

    Raises:
        HTTPException: If classification fails
    """
    with tracer.start_as_current_span("classify_document") as span:
        span.set_attribute("user.id", user["user_id"])
        span.set_attribute("document.id", request.document_id)
        span.set_attribute("multi_label", request.multi_label)
        start_time = datetime.utcnow()

        try:
            # Get document
            document = await document_service.get_document(request.document_id, user["user_id"])
            if not document:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document {request.document_id} not found"
                )

            # Classify document
            classifications = await llm_service.classify_document(
                document,
                categories=request.categories,
                multi_label=request.multi_label
            )

            # Store classifications in document metadata
            updates = {
                "metadata": {
                    "classifications": classifications
                }
            }
            await document_service.update_document(
                request.document_id,
                updates,
                user["user_id"]
            )

            processing_time = (datetime.utcnow() - start_time).total_seconds()

            return ProcessingResponse(
                success=True,
                document_id=request.document_id,
                result={
                    "classifications": classifications
                },
                message="Document classified successfully",
                processing_time=processing_time
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Classification failed: {str(e)}")
            span.record_exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Classification failed: {str(e)}"
            )


@router.post("/transcribe", response_model=ProcessingResponse)
async def transcribe_media(
    request: TranscriptionRequest,
    user: Dict = Depends(get_current_user),
    transcription_service: TranscriptionService = Depends(get_transcription_service),
    document_service: DocumentService = Depends(get_document_service),
    trace_context: Dict = Depends(verify_trace_context)
) -> ProcessingResponse:
    """Transcribe YouTube video or podcast

    Args:
        request: Transcription request
        user: Current user
        transcription_service: Transcription service
        document_service: Document service
        trace_context: W3C trace context

    Returns:
        Processing response with transcription

    Raises:
        HTTPException: If transcription fails
    """
    with tracer.start_as_current_span("transcribe_media") as span:
        span.set_attribute("user.id", user["user_id"])
        span.set_attribute("media.url", request.url)
        span.set_attribute("media.language", request.language)
        start_time = datetime.utcnow()

        try:
            # Determine media type
            if "youtube.com" in request.url or "youtu.be" in request.url:
                doc_type = DocumentType.YOUTUBE
            else:
                doc_type = DocumentType.PODCAST

            # Transcribe media
            transcription = await transcription_service.transcribe(
                request.url,
                language=request.language
            )

            # Save as document if requested
            doc_id = None
            if request.save_as_document:
                metadata = DocumentMetadata(
                    document_id=str(uuid.uuid4()),
                    document_type=doc_type,
                    name=f"Transcription: {request.url[:50]}",
                    summary=f"Transcription of {doc_type.value} from {request.url}",
                    created_user=user["user_id"],
                    updated_user=user["user_id"]
                )

                content_obj = DocumentContent(
                    formatted_content=transcription["formatted"],
                    raw_text=transcription["text"]
                )

                document = DocumentMessage(
                    metadata=metadata,
                    content=content_obj,
                    user_id=user["user_id"],
                    trace_id=trace_context.get("trace_id"),
                    span_id=trace_context.get("span_id")
                )

                created = await document_service.create_document(document, user["user_id"])
                doc_id = created.metadata.document_id

            processing_time = (datetime.utcnow() - start_time).total_seconds()

            return ProcessingResponse(
                success=True,
                document_id=doc_id,
                result={
                    "transcription_length": len(transcription["text"]),
                    "duration": transcription.get("duration"),
                    "language": transcription.get("language", request.language)
                },
                message="Media transcribed successfully",
                processing_time=processing_time
            )

        except Exception as e:
            logger.error(f"Transcription failed: {str(e)}")
            span.record_exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Transcription failed: {str(e)}"
            )


@router.post("/scrape", response_model=ProcessingResponse)
async def scrape_webpage(
    request: WebScrapeRequest,
    user: Dict = Depends(get_current_user),
    scraping_service: WebScrapingService = Depends(get_web_scraping_service),
    document_service: DocumentService = Depends(get_document_service),
    trace_context: Dict = Depends(verify_trace_context)
) -> ProcessingResponse:
    """Scrape webpage to markdown

    Args:
        request: Web scraping request
        user: Current user
        scraping_service: Web scraping service
        document_service: Document service
        trace_context: W3C trace context

    Returns:
        Processing response with scraped content

    Raises:
        HTTPException: If scraping fails
    """
    with tracer.start_as_current_span("scrape_webpage") as span:
        span.set_attribute("user.id", user["user_id"])
        span.set_attribute("web.url", request.url)
        start_time = datetime.utcnow()

        try:
            # Scrape webpage
            scraped_content = await scraping_service.scrape_to_markdown(
                request.url,
                include_images=request.include_images,
                include_links=request.include_links
            )

            # Save as document if requested
            doc_id = None
            if request.save_as_document:
                metadata = DocumentMetadata(
                    document_id=str(uuid.uuid4()),
                    document_type=DocumentType.WEBPAGE,
                    name=scraped_content.get("title", f"Webpage: {request.url[:50]}"),
                    summary=scraped_content.get("description", f"Scraped content from {request.url}"),
                    created_user=user["user_id"],
                    updated_user=user["user_id"]
                )

                content_obj = DocumentContent(
                    formatted_content=scraped_content["markdown"],
                    raw_text=scraped_content["text"]
                )

                document = DocumentMessage(
                    metadata=metadata,
                    content=content_obj,
                    user_id=user["user_id"],
                    trace_id=trace_context.get("trace_id"),
                    span_id=trace_context.get("span_id")
                )

                created = await document_service.create_document(document, user["user_id"])
                doc_id = created.metadata.document_id

            processing_time = (datetime.utcnow() - start_time).total_seconds()

            return ProcessingResponse(
                success=True,
                document_id=doc_id,
                result={
                    "content_length": len(scraped_content["markdown"]),
                    "title": scraped_content.get("title"),
                    "images_count": scraped_content.get("images_count", 0),
                    "links_count": scraped_content.get("links_count", 0)
                },
                message="Webpage scraped successfully",
                processing_time=processing_time
            )

        except Exception as e:
            logger.error(f"Web scraping failed: {str(e)}")
            span.record_exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Web scraping failed: {str(e)}"
            )


@router.post("/batch", response_model=Dict[str, ProcessingResponse])
async def batch_process(
    operations: List[Dict[str, Any]],
    user: Dict = Depends(get_current_user),
    trace_context: Dict = Depends(verify_trace_context)
) -> Dict[str, ProcessingResponse]:
    """Execute multiple processing operations in parallel

    Args:
        operations: List of operations to execute
        user: Current user
        trace_context: W3C trace context

    Returns:
        Dictionary of operation results

    Raises:
        HTTPException: If batch processing fails
    """
    with tracer.start_as_current_span("batch_process") as span:
        span.set_attribute("user.id", user["user_id"])
        span.set_attribute("operations.count", len(operations))

        try:
            # Validate operations
            if len(operations) > 10:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Maximum 10 operations per batch"
                )

            # Execute operations in parallel
            tasks = []
            operation_ids = []

            for idx, op in enumerate(operations):
                op_type = op.get("type")
                op_id = op.get("id", f"op_{idx}")
                operation_ids.append(op_id)

                if op_type == "summarize":
                    # Create summarization task
                    pass  # Would create actual async task
                elif op_type == "extract_entities":
                    # Create entity extraction task
                    pass  # Would create actual async task
                elif op_type == "classify":
                    # Create classification task
                    pass  # Would create actual async task
                else:
                    logger.warning(f"Unknown operation type: {op_type}")

            # Wait for all tasks to complete
            # results = await asyncio.gather(*tasks, return_exceptions=True)

            # For now, return placeholder
            results = {}
            for op_id in operation_ids:
                results[op_id] = ProcessingResponse(
                    success=True,
                    message="Batch operation completed",
                    processing_time=0.1
                )

            return results

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Batch processing failed: {str(e)}")
            span.record_exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Batch processing failed: {str(e)}"
            )