"""Document API endpoints"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import aiofiles
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from opentelemetry import trace

from ...models.document import (
    DocumentMessage,
    DocumentMetadata,
    DocumentContent,
    DocumentType,
    DocumentAction
)
from ...services.document_service import DocumentService
from ...services.pdf_service import PDFService
from ...core.logger import CentralizedLogger
from ..dependencies import (
    get_current_user,
    get_document_service,
    get_pdf_service,
    get_pagination,
    PaginationParams,
    verify_trace_context
)


router = APIRouter()
logger = CentralizedLogger("DocumentRouter")
tracer = trace.get_tracer(__name__)


# Request/Response models
from pydantic import BaseModel, Field


class CreateDocumentRequest(BaseModel):
    """Request model for creating a document"""
    name: str = Field(..., description="Document name")
    document_type: DocumentType = Field(..., description="Type of document")
    content: str = Field("", description="Document content")
    summary: Optional[str] = Field(None, description="Document summary")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class UpdateDocumentRequest(BaseModel):
    """Request model for updating a document"""
    name: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class DocumentResponse(BaseModel):
    """Response model for document operations"""
    document_id: str
    name: str
    document_type: DocumentType
    summary: Optional[str]
    version: int
    created_at: datetime
    updated_at: datetime
    created_user: str
    updated_user: str


class DocumentListResponse(BaseModel):
    """Response model for document list"""
    documents: List[DocumentResponse]
    total: int
    limit: int
    offset: int


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    request: CreateDocumentRequest,
    user: Dict = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
    trace_context: Dict = Depends(verify_trace_context)
) -> DocumentResponse:
    """Create a new document

    Args:
        request: Document creation request
        user: Current user
        service: Document service
        trace_context: W3C trace context

    Returns:
        Created document

    Raises:
        HTTPException: If creation fails
    """
    with tracer.start_as_current_span("create_document") as span:
        span.set_attribute("user.id", user["user_id"])
        span.set_attribute("document.type", request.document_type)

        try:
            # Create document message
            metadata = DocumentMetadata(
                document_id=f"doc_{datetime.utcnow().timestamp()}",
                document_type=request.document_type,
                name=request.name,
                summary=request.summary,
                created_user=user["user_id"],
                updated_user=user["user_id"]
            )

            content = DocumentContent(
                formatted_content=request.content,
                raw_text=request.content
            )

            document = DocumentMessage(
                metadata=metadata,
                content=content,
                user_id=user["user_id"],
                trace_id=trace_context.get("trace_id"),
                span_id=trace_context.get("span_id")
            )

            # Create document
            created = await service.create_document(document, user["user_id"])

            logger.info(f"Document created: {created.metadata.document_id}")

            return DocumentResponse(
                document_id=created.metadata.document_id,
                name=created.metadata.name,
                document_type=created.metadata.document_type,
                summary=created.metadata.summary,
                version=created.metadata.version,
                created_at=created.metadata.created_at,
                updated_at=created.metadata.updated_at,
                created_user=created.metadata.created_user,
                updated_user=created.metadata.updated_user
            )

        except ValueError as e:
            logger.warning(f"Document creation failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error creating document: {str(e)}")
            span.record_exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create document"
            )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    user: Dict = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service)
) -> DocumentResponse:
    """Get a document by ID

    Args:
        document_id: Document ID
        user: Current user
        service: Document service

    Returns:
        Document details

    Raises:
        HTTPException: If document not found
    """
    with tracer.start_as_current_span("get_document") as span:
        span.set_attribute("document.id", document_id)
        span.set_attribute("user.id", user["user_id"])

        document = await service.get_document(document_id, user["user_id"])

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )

        return DocumentResponse(
            document_id=document.metadata.document_id,
            name=document.metadata.name,
            document_type=document.metadata.document_type,
            summary=document.metadata.summary,
            version=document.metadata.version,
            created_at=document.metadata.created_at,
            updated_at=document.metadata.updated_at,
            created_user=document.metadata.created_user,
            updated_user=document.metadata.updated_user
        )


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str,
    request: UpdateDocumentRequest,
    user: Dict = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service)
) -> DocumentResponse:
    """Update a document

    Args:
        document_id: Document ID
        request: Update request
        user: Current user
        service: Document service

    Returns:
        Updated document

    Raises:
        HTTPException: If update fails
    """
    with tracer.start_as_current_span("update_document") as span:
        span.set_attribute("document.id", document_id)
        span.set_attribute("user.id", user["user_id"])

        # Build update dict
        updates = {}
        if request.name is not None:
            updates["metadata"] = updates.get("metadata", {})
            updates["metadata"]["name"] = request.name
        if request.summary is not None:
            updates["metadata"] = updates.get("metadata", {})
            updates["metadata"]["summary"] = request.summary
        if request.content is not None:
            updates["content"] = {
                "formatted_content": request.content,
                "raw_text": request.content
            }
        if request.metadata is not None:
            updates["metadata"] = updates.get("metadata", {})
            updates["metadata"].update(request.metadata)

        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No updates provided"
            )

        updated = await service.update_document(document_id, updates, user["user_id"])

        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )

        return DocumentResponse(
            document_id=updated.metadata.document_id,
            name=updated.metadata.name,
            document_type=updated.metadata.document_type,
            summary=updated.metadata.summary,
            version=updated.metadata.version,
            created_at=updated.metadata.created_at,
            updated_at=updated.metadata.updated_at,
            created_user=updated.metadata.created_user,
            updated_user=updated.metadata.updated_user
        )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    soft_delete: bool = Query(True, description="Soft delete (recoverable) or hard delete"),
    user: Dict = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service)
):
    """Delete a document

    Args:
        document_id: Document ID
        soft_delete: Whether to soft delete (recoverable) or hard delete
        user: Current user
        service: Document service

    Raises:
        HTTPException: If delete fails
    """
    with tracer.start_as_current_span("delete_document") as span:
        span.set_attribute("document.id", document_id)
        span.set_attribute("user.id", user["user_id"])
        span.set_attribute("soft_delete", soft_delete)

        success = await service.delete_document(
            document_id,
            user["user_id"],
            soft_delete=soft_delete
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )

        logger.info(f"Document deleted: {document_id} (soft={soft_delete})")


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    user: Dict = Depends(get_current_user),
    pagination: PaginationParams = Depends(get_pagination),
    service: DocumentService = Depends(get_document_service),
    document_type: Optional[DocumentType] = None,
    search: Optional[str] = None
) -> DocumentListResponse:
    """List documents with pagination

    Args:
        user: Current user
        pagination: Pagination parameters
        service: Document service
        document_type: Filter by document type
        search: Search query

    Returns:
        List of documents
    """
    with tracer.start_as_current_span("list_documents") as span:
        span.set_attribute("user.id", user["user_id"])
        span.set_attribute("limit", pagination.limit)
        span.set_attribute("offset", pagination.offset)

        # Get documents
        if search:
            documents = await service.search_documents(search, user["user_id"])
        else:
            documents = await service.list_documents(
                user_id=user["user_id"],
                limit=pagination.limit,
                offset=pagination.offset
            )

        # Filter by type if specified
        if document_type:
            documents = [
                doc for doc in documents
                if doc.document_type == document_type
            ]

        # Convert to response format
        doc_responses = [
            DocumentResponse(
                document_id=doc.document_id,
                name=doc.name,
                document_type=doc.document_type,
                summary=doc.summary,
                version=doc.version,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
                created_user=doc.created_user,
                updated_user=doc.updated_user
            )
            for doc in documents[pagination.offset:pagination.offset + pagination.limit]
        ]

        return DocumentListResponse(
            documents=doc_responses,
            total=len(documents),
            limit=pagination.limit,
            offset=pagination.offset
        )


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    name: Optional[str] = None,
    user: Dict = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
    pdf_service: PDFService = Depends(get_pdf_service),
    trace_context: Dict = Depends(verify_trace_context)
) -> DocumentResponse:
    """Upload a document file

    Args:
        file: Uploaded file
        name: Optional document name
        user: Current user
        service: Document service
        pdf_service: PDF service for PDF files
        trace_context: W3C trace context

    Returns:
        Created document

    Raises:
        HTTPException: If upload fails
    """
    with tracer.start_as_current_span("upload_document") as span:
        span.set_attribute("user.id", user["user_id"])
        span.set_attribute("file.name", file.filename)
        span.set_attribute("file.size", file.size if hasattr(file, 'size') else 0)

        try:
            # Determine document type from file extension
            file_ext = Path(file.filename).suffix.lower()
            doc_type_map = {
                '.pdf': DocumentType.PDF,
                '.docx': DocumentType.WORD,
                '.doc': DocumentType.WORD,
                '.xlsx': DocumentType.EXCEL,
                '.xls': DocumentType.EXCEL,
                '.json': DocumentType.JSON,
                '.xml': DocumentType.XML,
                '.md': DocumentType.MARKDOWN,
                '.csv': DocumentType.CSV
            }

            doc_type = doc_type_map.get(file_ext)
            if not doc_type:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported file type: {file_ext}"
                )

            # Save file temporarily
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                content = await file.read()
                await aiofiles.open(tmp_file.name, 'wb').write(content)
                tmp_path = tmp_file.name

            try:
                # Process based on file type
                if doc_type == DocumentType.PDF:
                    # Convert PDF to markdown
                    markdown_content = await pdf_service.pdf_to_markdown(tmp_path)
                    formatted_content = markdown_content
                    raw_text = markdown_content
                else:
                    # For other types, read as text for now
                    async with aiofiles.open(tmp_path, 'r', encoding='utf-8', errors='ignore') as f:
                        raw_text = await f.read()
                    formatted_content = raw_text

                # Create document
                metadata = DocumentMetadata(
                    document_id=f"doc_{datetime.utcnow().timestamp()}",
                    document_type=doc_type,
                    name=name or file.filename,
                    created_user=user["user_id"],
                    updated_user=user["user_id"]
                )

                content_obj = DocumentContent(
                    formatted_content=formatted_content,
                    raw_text=raw_text
                )

                document = DocumentMessage(
                    metadata=metadata,
                    content=content_obj,
                    user_id=user["user_id"],
                    trace_id=trace_context.get("trace_id"),
                    span_id=trace_context.get("span_id")
                )

                # Create document
                created = await service.create_document(document, user["user_id"])

                logger.info(f"Document uploaded: {created.metadata.document_id}")

                return DocumentResponse(
                    document_id=created.metadata.document_id,
                    name=created.metadata.name,
                    document_type=created.metadata.document_type,
                    summary=created.metadata.summary,
                    version=created.metadata.version,
                    created_at=created.metadata.created_at,
                    updated_at=created.metadata.updated_at,
                    created_user=created.metadata.created_user,
                    updated_user=created.metadata.updated_user
                )

            finally:
                # Clean up temp file
                os.unlink(tmp_path)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to upload document: {str(e)}")
            span.record_exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process uploaded file: {str(e)}"
            )


@router.get("/{document_id}/versions")
async def get_document_versions(
    document_id: str,
    user: Dict = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service)
) -> List[Dict[str, Any]]:
    """Get document version history

    Args:
        document_id: Document ID
        user: Current user
        service: Document service

    Returns:
        List of document versions
    """
    with tracer.start_as_current_span("get_document_versions") as span:
        span.set_attribute("document.id", document_id)
        span.set_attribute("user.id", user["user_id"])

        versions = await service.get_document_versions(document_id, user["user_id"])

        return [
            {
                "version": v.version_number,
                "created_at": v.created_at,
                "created_by": v.created_by,
                "change_summary": v.change_summary
            }
            for v in versions
        ]