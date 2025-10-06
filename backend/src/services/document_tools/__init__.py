"""Document processing tools system

This package provides a decorator-based tool registration system for document processing.
Tools are automatically discovered on startup and can be dynamically executed via API.
"""

from .base_tool import (
    BaseDocumentTool,
    DocumentToolMetadata,
    ToolCategory,
    DocumentToolCategory,
    DocumentToolCapability,
)
from .tool_registry import DocumentToolRegistry, DocumentToolType
from .tool_decorators import register_document_tool, initialize_document_tools

__all__ = [
    "BaseDocumentTool",
    "DocumentToolMetadata",
    "ToolCategory",
    "DocumentToolCategory",
    "DocumentToolCapability",
    "DocumentToolRegistry",
    "DocumentToolType",
    "register_document_tool",
    "initialize_document_tools",
]
