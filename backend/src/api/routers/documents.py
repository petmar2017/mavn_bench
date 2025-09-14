"""Document API endpoints"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import uuid
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


class DocumentListResponse(BaseModel):
    """Response model for document list"""
    documents: List[DocumentMessage]
    total: int
    limit: int
    offset: int


@router.post("/", response_model=DocumentMessage, status_code=status.HTTP_201_CREATED)
async def create_document(
    request: CreateDocumentRequest,
    user: Dict = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
    trace_context: Dict = Depends(verify_trace_context)
) -> DocumentMessage:
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
                document_id=str(uuid.uuid4()),
                document_type=request.document_type,
                name=request.name,
                summary=request.summary,
                file_size=len(request.content.encode('utf-8')) if request.content else 0,  # Calculate file size from content
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

            return created

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


@router.get("/trash")
async def list_deleted_documents(
    user: Dict = Depends(get_current_user),
    pagination: PaginationParams = Depends(get_pagination),
    service: DocumentService = Depends(get_document_service),
    document_type: Optional[DocumentType] = None
) -> Dict[str, Any]:
    """List soft-deleted documents (trash)

    Args:
        user: Current user
        pagination: Pagination parameters
        service: Document service
        document_type: Filter by document type

    Returns:
        List of deleted documents
    """
    with tracer.start_as_current_span("list_deleted_documents") as span:
        span.set_attribute("user.id", user["user_id"])
        span.set_attribute("pagination.limit", pagination.limit)
        span.set_attribute("pagination.offset", pagination.offset)

        # Get documents including deleted ones
        documents = await service.list_documents(
            user_id=user["user_id"],
            document_type=document_type,
            limit=pagination.limit + pagination.offset,
            offset=0,
            include_deleted=True  # Include deleted documents
        )

        # Filter to only show deleted documents
        deleted_docs = [doc for doc in documents if getattr(doc, "deleted", False)]

        # Convert to response format
        doc_responses = []
        for doc in deleted_docs[pagination.offset:pagination.offset + pagination.limit]:
            doc_response = {
                "metadata": {
                    "document_id": doc.document_id,
                    "name": doc.name,
                    "document_type": doc.document_type,
                    "version": doc.version,
                    "size": doc.file_size if hasattr(doc, 'file_size') and doc.file_size else 0,
                    "created_at": doc.created_at.isoformat() if hasattr(doc.created_at, 'isoformat') else str(doc.created_at),
                    "updated_at": doc.updated_at.isoformat() if hasattr(doc.updated_at, 'isoformat') else str(doc.updated_at),
                    "deleted_at": doc.deleted_at.isoformat() if hasattr(doc, 'deleted_at') and doc.deleted_at and hasattr(doc.deleted_at, 'isoformat') else str(doc.deleted_at) if hasattr(doc, 'deleted_at') and doc.deleted_at else None,
                    "deleted_by": doc.deleted_by if hasattr(doc, 'deleted_by') else None,
                    "deleted": True,
                    "user_id": doc.created_user,
                    "tags": [],
                    "processing_status": "completed"
                },
                "content": {
                    "summary": doc.summary
                }
            }
            doc_responses.append(doc_response)

        return {
            "documents": doc_responses,
            "total": len(deleted_docs),
            "limit": pagination.limit,
            "offset": pagination.offset
        }


@router.get("/{document_id}", response_model=DocumentMessage)
async def get_document(
    document_id: str,
    user: Dict = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service)
) -> DocumentMessage:
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

        return document


@router.get("/{document_id}/content")
async def get_document_content(
    document_id: str,
    user: Dict = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service)
) -> Dict[str, Any]:
    """Get document content

    Args:
        document_id: Document ID
        user: Current user
        service: Document service

    Returns:
        Document content

    Raises:
        HTTPException: If document not found
    """
    with tracer.start_as_current_span("get_document_content") as span:
        span.set_attribute("document.id", document_id)
        span.set_attribute("user.id", user["user_id"])

        document = await service.get_document(document_id, user["user_id"])

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )

        # Extract content from document
        content_data = {
            "document_id": document_id,
            "content": {
                "text": getattr(document.content, 'text', None) if document.content else None,
                "formatted_content": getattr(document.content, 'formatted_content', None) if document.content else None,
                "raw_text": getattr(document.content, 'raw_text', None) if document.content else None,
                "summary": document.metadata.summary if document.metadata else None
            }
        }

        return content_data


@router.put("/{document_id}", response_model=DocumentMessage)
async def update_document(
    document_id: str,
    request: UpdateDocumentRequest,
    user: Dict = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service)
) -> DocumentMessage:
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

        return updated


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


@router.get("/")
async def list_documents(
    user: Dict = Depends(get_current_user),
    pagination: PaginationParams = Depends(get_pagination),
    service: DocumentService = Depends(get_document_service),
    document_type: Optional[DocumentType] = None,
    search: Optional[str] = None
) -> Dict[str, Any]:
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

        # Convert to response format that matches frontend expectations
        doc_responses = []
        for doc in documents[pagination.offset:pagination.offset + pagination.limit]:
            # Build the response in the format frontend expects
            doc_response = {
                "metadata": {
                    "document_id": doc.document_id,
                    "name": doc.name,
                    "document_type": doc.document_type,
                    "version": doc.version,
                    "size": doc.file_size if hasattr(doc, 'file_size') and doc.file_size else 0,  # Use actual file size from metadata
                    "created_at": doc.created_at.isoformat() if hasattr(doc.created_at, 'isoformat') else str(doc.created_at),
                    "updated_at": doc.updated_at.isoformat() if hasattr(doc.updated_at, 'isoformat') else str(doc.updated_at),
                    "deleted": getattr(doc, "deleted", False),
                    "deleted_at": doc.deleted_at.isoformat() if hasattr(doc, 'deleted_at') and doc.deleted_at and hasattr(doc.deleted_at, 'isoformat') else str(doc.deleted_at) if hasattr(doc, 'deleted_at') and doc.deleted_at else None,
                    "deleted_by": doc.deleted_by if hasattr(doc, 'deleted_by') else None,
                    "user_id": doc.created_user,
                    "tags": [],
                    "processing_status": "completed",
                    "summary": doc.summary,
                    "language": getattr(doc, "language", "en")
                },
                "content": {
                    "summary": doc.summary
                }
            }
            doc_responses.append(doc_response)

        return {
            "documents": doc_responses,
            "total": len(documents),
            "limit": pagination.limit,
            "offset": pagination.offset
        }




@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    name: Optional[str] = None,
    user: Dict = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
    pdf_service: PDFService = Depends(get_pdf_service),
    trace_context: Dict = Depends(verify_trace_context)
) -> Dict[str, Any]:
    """Upload a document file for async processing

    Args:
        file: Uploaded file
        name: Optional document name
        user: Current user
        service: Document service
        pdf_service: PDF service for PDF files
        trace_context: W3C trace context

    Returns:
        Job information with document ID and job ID

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
                '.txt': DocumentType.TEXT,
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
                tmp_path = tmp_file.name

            # Write content to temp file using aiofiles correctly
            async with aiofiles.open(tmp_path, 'wb') as f:
                await f.write(content)

            try:
                # Import queue service
                from ...services.queue_service import queue_service
                from ...models.document import ProcessingStage

                # Create document with PENDING status
                document_id = str(uuid.uuid4())
                metadata = DocumentMetadata(
                    document_id=document_id,
                    document_type=doc_type,
                    name=name or file.filename,
                    summary="Waiting for processing...",  # Will be replaced during processing
                    language="en",  # Default, will be detected during processing
                    file_size=len(content),
                    created_user=user["user_id"],
                    updated_user=user["user_id"],
                    processing_stage=ProcessingStage.PENDING  # Set initial status
                )

                # Create minimal content for now
                content_obj = DocumentContent(
                    formatted_content="",  # Will be populated during processing
                    raw_text=""  # Will be populated during processing
                )

                document = DocumentMessage(
                    metadata=metadata,
                    content=content_obj,
                    user_id=user["user_id"],
                    trace_id=trace_context.get("trace_id"),
                    span_id=trace_context.get("span_id")
                )

                # Create document in database with PENDING status
                created = await service.create_document(document, user["user_id"])

                # Add to processing queue
                job_id = await queue_service.enqueue_document(
                    document_id=document_id,
                    user_id=user["user_id"],
                    file_path=tmp_path,
                    file_type=doc_type.value,
                    metadata={
                        "original_filename": file.filename,
                        "content_type": file.content_type,
                        "file_size": len(content)
                    }
                )

                logger.info(f"Document queued for processing: {document_id}, job_id: {job_id}")

                # Return format that frontend expects with job information
                return {
                    "id": document_id,
                    "job_id": job_id,  # Include job ID for status tracking
                    "metadata": {
                        "document_id": document_id,
                        "name": created.metadata.name,
                        "document_type": created.metadata.document_type.value,
                        "version": created.metadata.version,
                        "size": len(content),
                        "created_at": created.metadata.created_at.isoformat(),
                        "updated_at": created.metadata.updated_at.isoformat(),
                        "user_id": user["user_id"],
                        "tags": [],
                        "processing_status": ProcessingStage.PENDING.value  # Status is pending
                    },
                    "content": {
                        "raw_content": None,  # No content yet
                        "formatted_content": None,  # No content yet
                        "summary": "Waiting for processing..."  # Status message
                    },
                    "queue_position": 1  # Will be updated by queue service
                }

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