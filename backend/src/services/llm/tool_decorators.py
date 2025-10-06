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


def scan_and_import_tools(
    package_path: str = "src.services.llm.tools"
) -> List[str]:
    """Scan and import all tool modules to trigger decorator registration

    This function dynamically imports all tool modules in the specified package
    to ensure their @register_tool decorators are executed.

    Args:
        package_path: Python package path containing tool modules

    Returns:
        List of imported module names
    """
    import importlib
    from pathlib import Path

    imported_modules = []

    try:
        # Get the tools directory
        base_path = Path(__file__).parent / "tools"

        if not base_path.exists():
            return imported_modules

        # Import all Python files ending with _tool.py
        for file_path in base_path.glob("*_tool.py"):
            if file_path.name.startswith("__"):
                continue  # Skip __init__.py and __pycache__

            module_name = file_path.stem
            full_module_path = f"{package_path}.{module_name}"

            try:
                importlib.import_module(full_module_path)
                imported_modules.append(full_module_path)
            except ImportError as e:
                # Log warning but continue with other modules
                print(f"Warning: Could not import tool module {full_module_path}: {e}")

    except Exception as e:
        print(f"Error scanning tool modules: {e}")

    return imported_modules


def initialize_llm_tools() -> Dict[str, int]:
    """Initialize the LLM tool system by scanning and registering all tools

    This is the main initialization function that should be called during
    application startup. It:
    1. Scans for tool modules and imports them
    2. Registers all decorated tools
    3. Returns initialization statistics

    Returns:
        Dictionary with initialization statistics
    """
    # Scan and import tool modules
    imported_modules = scan_and_import_tools()

    # Register all decorated tools
    registered_count = auto_register_decorated_tools()

    # Get registry statistics
    available_tools = ToolRegistry.get_available_tools()

    return {
        "imported_modules": imported_modules,
        "imported_module_count": len(imported_modules),
        "registered_tools": registered_count,
        "total_tools": len(available_tools),
    }