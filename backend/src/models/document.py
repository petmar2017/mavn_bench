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

class DocumentMetadata(BaseModel):
    document_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_type: DocumentType
    name: str
    summary: Optional[str] = None
    access_permission: AccessPermission = AccessPermission.READ
    access_group: AccessGroup = AccessGroup.ME
    created_timestamp: datetime = Field(default_factory=datetime.utcnow)
    created_user: str
    updated_timestamp: datetime = Field(default_factory=datetime.utcnow)
    updated_user: str
    version: int = 1
    tags: List[str] = Field(default_factory=list)
    source_url: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None

class DocumentContent(BaseModel):
    formatted_content: Optional[str] = Field(None, description="Markdown formatted content")
    raw_text: Optional[str] = Field(None, description="Plain text content")
    structured_data: Optional[Dict[str, Any]] = Field(None, description="For JSON, XML, CSV")
    binary_data: Optional[str] = Field(None, description="Base64 encoded binary")
    embeddings: Optional[List[float]] = Field(None, description="Vector embeddings for search")

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
