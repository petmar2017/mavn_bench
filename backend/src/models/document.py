"""Document models for Mavn Bench"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import uuid

class AccessPermission(str, Enum):
    READ = "read"
    WRITE = "write"
    SUMMARY_ONLY = "summary_only"

class AccessGroup(str, Enum):
    ME = "me"
    GROUP = "group"
    COMPANY = "company"
    WORLD = "world"

class DocumentType(str, Enum):
    PDF = "pdf"
    WORD = "word"
    EXCEL = "excel"
    TEXT = "text"
    JSON = "json"
    XML = "xml"
    PODCAST = "podcast"
    YOUTUBE = "youtube"
    WEBPAGE = "webpage"
    MARKDOWN = "markdown"
    CSV = "csv"

class DocumentAction(str, Enum):
    VIEW = "view"
    EDIT = "edit"
    SAVE = "save"
    DELETE = "delete"
    TOOLS = "tools"
    TOOLS_ANALYSIS = "tools_analysis"
    SEARCH = "search"
    FILTER = "filter"
    RESET_FILTER = "reset_filter"

class ProcessingStage(str, Enum):
    """Processing stage for documents"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class DocumentSource(str, Enum):
    """Source of the document"""
    UPLOAD = "upload"
    WEB = "web"
    YOUTUBE = "youtube"
    API = "api"
    MANUAL = "manual"

class DocumentMetadata(BaseModel):
    # Core identifiers (support both patterns)
    document_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    id: Optional[str] = None  # Alias for document_id

    # Document classification
    document_type: DocumentType
    type: Optional[DocumentType] = None  # Alias for document_type

    # Document info
    name: str
    title: Optional[str] = None  # Alias for name
    summary: Optional[str] = None
    language: Optional[str] = Field(default="en", description="ISO 639-1 language code")

    # Access control
    access_permission: AccessPermission = AccessPermission.READ
    access_group: AccessGroup = AccessGroup.ME

    # Timestamps (support both patterns)
    created_timestamp: datetime = Field(default_factory=datetime.utcnow)
    created_at: Optional[datetime] = None  # Alias
    created_user: str

    updated_timestamp: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None  # Alias
    updated_user: str

    # Version and processing
    version: int = 1
    processing_stage: Optional[ProcessingStage] = ProcessingStage.PENDING

    @property
    def processing_status(self) -> Optional[str]:
        """Alias for processing_stage for frontend compatibility"""
        return self.processing_stage.value if self.processing_stage else None

    # Source and references
    source: Optional[DocumentSource] = None
    source_url: Optional[str] = None
    original_url: Optional[str] = None  # Alias for source_url

    # Metadata
    tags: List[str] = Field(default_factory=list)
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    file_path: Optional[str] = Field(default=None, description="Path to original file if stored")
    entities: Optional[List[Dict[str, Any]]] = Field(default=None, description="Extracted entities from document")
    relationships: Optional[List[Dict[str, Any]]] = Field(default=None, description="Entity relationships")

    # Soft delete fields
    deleted: bool = Field(default=False, description="Whether the document is soft deleted")
    deleted_at: Optional[datetime] = Field(default=None, description="When the document was deleted")
    deleted_by: Optional[str] = Field(default=None, description="User who deleted the document")

    # Queue processing fields
    retry_count: int = Field(default=0, description="Number of processing retry attempts")
    last_error: Optional[str] = Field(default=None, description="Last error message from processing")

    def model_post_init(self, __context):
        """Handle field aliases after initialization"""
        # Sync id with document_id
        if self.id and not self.document_id:
            self.document_id = self.id
        elif self.document_id and not self.id:
            self.id = self.document_id

        # Sync type with document_type
        if self.type and not self.document_type:
            self.document_type = self.type
        elif self.document_type and not self.type:
            self.type = self.document_type

        # Sync title with name
        if self.title and not self.name:
            self.name = self.title
        elif self.name and not self.title:
            self.title = self.name

        # Sync timestamps
        if self.created_at and not self.created_timestamp:
            self.created_timestamp = self.created_at
        elif self.created_timestamp and not self.created_at:
            self.created_at = self.created_timestamp

        if self.updated_at and not self.updated_timestamp:
            self.updated_timestamp = self.updated_at
        elif self.updated_timestamp and not self.updated_at:
            self.updated_at = self.updated_timestamp

        # Sync URLs
        if self.original_url and not self.source_url:
            self.source_url = self.original_url
        elif self.source_url and not self.original_url:
            self.original_url = self.source_url

class ContentBlock(BaseModel):
    """A block of content with type and metadata"""
    type: str  # text, markdown, code, image, etc.
    content: str
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class DocumentContent(BaseModel):
    formatted_content: Optional[str] = Field(None, description="Markdown formatted content")
    raw_text: Optional[str] = Field(None, description="Plain text content")
    structured_data: Optional[Dict[str, Any]] = Field(None, description="For JSON, XML, CSV")
    binary_data: Optional[str] = Field(None, description="Base64 encoded binary")
    embeddings: Optional[List[float]] = Field(None, description="Vector embeddings for search")
    blocks: Optional[List[ContentBlock]] = Field(default_factory=list, description="Content blocks")

class DocumentVersion(BaseModel):
    version: int
    timestamp: datetime
    user: str
    changes: Dict[str, Any]
    commit_message: Optional[str] = None

class AuditLogEntry(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user: str
    action: str
    details: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class DocumentMessage(BaseModel):
    """Core message format passed between all components"""
    metadata: DocumentMetadata
    content: DocumentContent
    action: Optional[DocumentAction] = None
    tools: List[str] = Field(default_factory=list)
    history: List[DocumentVersion] = Field(default_factory=list)
    audit_log: List[AuditLogEntry] = Field(default_factory=list)
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
