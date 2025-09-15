"""Tool registration decorators for automatic discovery"""

from typing import Type, Optional, List, Dict
from functools import wraps

from .tool_registry import LLMToolType, ToolRegistry
from .base_tool import BaseLLMTool


# Registry for decorated tools
_decorated_tools: Dict[LLMToolType, Type[BaseLLMTool]] = {}


def register_tool(
    tool_type: LLMToolType,
    aliases: Optional[List[LLMToolType]] = None
):
    """Decorator to automatically register LLM tools

    This decorator enables automatic discovery and registration of tools
    without requiring manual registration code.

    Args:
        tool_type: Primary tool type for registration
        aliases: Optional list of additional tool types this tool handles

    Example:
        @register_tool(LLMToolType.SUMMARIZATION)
        class SummarizationTool(BaseLLMTool):
            pass

        @register_tool(
            LLMToolType.MARKDOWN_FORMATTING,
            aliases=[LLMToolType.TEXT_TO_MARKDOWN]
        )
        class MarkdownFormattingTool(BaseLLMTool):
            pass
    """
    def decorator(cls: Type[BaseLLMTool]) -> Type[BaseLLMTool]:
        if not issubclass(cls, BaseLLMTool):
            raise ValueError(f"{cls.__name__} must inherit from BaseLLMTool")

        # Store in decorated tools registry
        _decorated_tools[tool_type] = cls

        # Store aliases if provided
        if aliases:
            for alias in aliases:
                _decorated_tools[alias] = cls

        # Add metadata to the class for introspection
        cls._tool_type = tool_type
        cls._tool_aliases = aliases or []

        return cls

    return decorator


def get_decorated_tools() -> Dict[LLMToolType, Type[BaseLLMTool]]:
    """Get all tools registered via decorators

    Returns:
        Dictionary mapping tool types to tool classes
    """
    return _decorated_tools.copy()


def clear_decorated_tools():
    """Clear the decorated tools registry (mainly for testing)"""
    _decorated_tools.clear()


def auto_register_decorated_tools():
    """Register all decorated tools with the ToolRegistry

    This function should be called during initialization to register
    all tools that have been decorated with @register_tool

    Returns:
        Number of tools registered
    """
    count = 0
    for tool_type, tool_class in _decorated_tools.items():
        ToolRegistry.register(tool_type, tool_class)
        count += 1

    return count