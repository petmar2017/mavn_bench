"""Tool registration decorators for automatic discovery"""

from functools import wraps
from typing import Dict, List, Optional, Type

from .base_tool import BaseTool
from .tool_registry import ToolRegistry

# Registry for decorated tools
_decorated_tools: Dict[str, Type[BaseTool]] = {}


def register_tool(tool_id: str, aliases: Optional[List[str]] = None):
    """Decorator to automatically register tools

    This decorator enables automatic discovery and registration of tools
    without requiring manual registration code.

    Args:
        tool_id: Unique tool identifier
        aliases: Optional list of additional IDs this tool handles

    Example:
        @register_tool("summarize")
        class SummarizationTool(BaseTool):
            pass

        @register_tool("markdown_format", aliases=["text_to_markdown"])
        class MarkdownFormattingTool(BaseTool):
            pass
    """

    def decorator(cls: Type[BaseTool]) -> Type[BaseTool]:
        if not issubclass(cls, BaseTool):
            raise ValueError(f"{cls.__name__} must inherit from BaseTool")

        # Store in decorated tools registry
        _decorated_tools[tool_id] = cls

        # Store aliases if provided
        if aliases:
            for alias in aliases:
                _decorated_tools[alias] = cls

        # Add metadata to class for introspection
        cls._tool_id = tool_id
        cls._tool_aliases = aliases or []

        return cls

    return decorator


def get_decorated_tools() -> Dict[str, Type[BaseTool]]:
    """Get all tools registered via decorators

    Returns:
        Dictionary mapping tool IDs to tool classes
    """
    return _decorated_tools.copy()


def clear_decorated_tools():
    """Clear the decorated tools registry (mainly for testing)"""
    _decorated_tools.clear()


def initialize_tools() -> int:
    """Register all decorated tools with the ToolRegistry

    This function should be called during app initialization to register
    all tools that have been decorated with @register_tool

    Returns:
        Number of tools registered
    """
    count = 0
    for tool_id, tool_class in _decorated_tools.items():
        ToolRegistry.register(tool_id, tool_class)
        count += 1

    return count


def auto_discover_tools(package_paths: List[str]) -> int:
    """Automatically discover and import tool modules

    Args:
        package_paths: List of Python package paths to scan for tools

    Returns:
        Number of tools discovered and registered
    """
    import importlib
    import pkgutil

    count = 0

    for package_path in package_paths:
        try:
            # Import the package
            package = importlib.import_module(package_path)

            # Find all submodules
            if hasattr(package, "__path__"):
                for _, name, is_pkg in pkgutil.iter_modules(package.__path__):
                    module_name = f"{package_path}.{name}"
                    try:
                        importlib.import_module(module_name)
                    except Exception as e:
                        # Log but don't fail on individual module errors
                        print(f"Warning: Could not import {module_name}: {str(e)}")

        except Exception as e:
            print(f"Warning: Could not scan package {package_path}: {str(e)}")

    # Register all discovered tools
    count = initialize_tools()

    return count
