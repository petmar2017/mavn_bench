"""Tool registration decorators for automatic discovery of document tools"""

from typing import Type, Optional, List, Dict
from functools import wraps

from .tool_registry import DocumentToolType, DocumentToolRegistry
from .base_tool import BaseDocumentTool


# Registry for decorated tools
_decorated_tools: Dict[DocumentToolType, Type[BaseDocumentTool]] = {}


def register_document_tool(
    tool_type: DocumentToolType,
    aliases: Optional[List[DocumentToolType]] = None
):
    """Decorator to automatically register document processing tools

    This decorator enables automatic discovery and registration of tools
    without requiring manual registration code. Tools are discovered
    on application startup via import scanning.

    Args:
        tool_type: Primary tool type for registration
        aliases: Optional list of additional tool types this tool handles

    Example:
        @register_document_tool(DocumentToolType.VALIDATE_JSON)
        class ValidateJSONTool(BaseDocumentTool):
            def execute(self, document, parameters=None):
                # Validate JSON content
                pass

        @register_document_tool(
            DocumentToolType.SENTIMENT_ANALYSIS,
            aliases=[DocumentToolType.EXTRACT_ENTITIES]
        )
        class SentimentAnalysisTool(BaseDocumentTool):
            # Tool that can handle both sentiment and entity extraction
            pass
    """
    def decorator(cls: Type[BaseDocumentTool]) -> Type[BaseDocumentTool]:
        if not issubclass(cls, BaseDocumentTool):
            raise ValueError(f"{cls.__name__} must inherit from BaseDocumentTool")

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


def get_decorated_tools() -> Dict[DocumentToolType, Type[BaseDocumentTool]]:
    """Get all tools registered via decorators

    Returns:
        Dictionary mapping tool types to tool classes
    """
    return _decorated_tools.copy()


def clear_decorated_tools():
    """Clear the decorated tools registry (mainly for testing)"""
    _decorated_tools.clear()


def auto_register_decorated_tools():
    """Register all decorated tools with the DocumentToolRegistry

    This function should be called during initialization to register
    all tools that have been decorated with @register_document_tool.
    It scans for decorated tools and registers them with the main registry.

    Returns:
        Number of tools registered
    """
    count = 0
    registered_classes = set()  # Track unique classes to avoid duplicate registration

    for tool_type, tool_class in _decorated_tools.items():
        # Avoid registering the same class multiple times for aliases
        if tool_class not in registered_classes:
            DocumentToolRegistry.register(tool_type, tool_class)
            registered_classes.add(tool_class)
            count += 1

    return count


def scan_and_import_tools(package_path: str = "src.services.document_tools.tools"):
    """Scan and import all tool modules to trigger decorator registration

    This function dynamically imports all tool modules in the specified package
    to ensure their @register_document_tool decorators are executed.

    Args:
        package_path: Python package path containing tool modules

    Returns:
        List of imported module names
    """
    import os
    import importlib
    import pkgutil
    from pathlib import Path

    imported_modules = []

    try:
        # Convert package path to filesystem path
        package_parts = package_path.split('.')
        base_path = Path(__file__).parent

        # Navigate to the tools directory
        tools_path = base_path / "tools"

        if not tools_path.exists():
            return imported_modules

        # Import all Python files in the tools directory
        for file_path in tools_path.glob("*.py"):
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


def initialize_document_tools():
    """Initialize the document tool system by scanning and registering all tools

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
    from .tool_registry import DocumentToolRegistry
    stats = DocumentToolRegistry.get_stats()

    return {
        "imported_modules": imported_modules,
        "imported_module_count": len(imported_modules),
        "registered_tools": registered_count,
        "total_tools": stats["total_tools"],
        "registry_stats": stats
    }


# Utility functions for tool introspection
def get_tool_type_for_class(tool_class: Type[BaseDocumentTool]) -> Optional[DocumentToolType]:
    """Get the primary tool type for a tool class

    Args:
        tool_class: Tool class to inspect

    Returns:
        Primary tool type or None if not found
    """
    return getattr(tool_class, '_tool_type', None)


def get_tool_aliases_for_class(tool_class: Type[BaseDocumentTool]) -> List[DocumentToolType]:
    """Get the aliases for a tool class

    Args:
        tool_class: Tool class to inspect

    Returns:
        List of tool type aliases
    """
    return getattr(tool_class, '_tool_aliases', [])


def is_tool_decorated(tool_class: Type[BaseDocumentTool]) -> bool:
    """Check if a tool class has been decorated

    Args:
        tool_class: Tool class to check

    Returns:
        True if decorated, False otherwise
    """
    return hasattr(tool_class, '_tool_type')