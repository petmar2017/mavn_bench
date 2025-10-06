"""Generic tool system for Mavn Bench

This package provides a unified tool system supporting:
- LLM-based tools (OpenAI, Anthropic, etc.)
- MCP-based tools (external tool servers)
- Executable tools (Python scripts, binaries)
- Document processing tools

All tools follow a common interface with:
- Metadata (name, description, capabilities)
- Input/output schemas
- Async execution
- Auto-registration via decorators
"""

from .base_tool import (BaseTool, ToolCapability, ToolCategory,
                        ToolExecutionContext, ToolMetadata)
from .tool_decorators import initialize_tools, register_tool
from .tool_registry import ToolRegistry, ToolType

__all__ = [
    "BaseTool",
    "ToolMetadata",
    "ToolCapability",
    "ToolCategory",
    "ToolExecutionContext",
    "ToolRegistry",
    "ToolType",
    "register_tool",
    "initialize_tools",
]
