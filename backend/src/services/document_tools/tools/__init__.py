"""Document processing tool implementations"""

# This module contains concrete implementations of document processing tools.
# Tools are automatically discovered and registered via decorators.

# Import all tool modules to trigger decorator registration
try:
    from . import validate_json_tool
    from . import sentiment_analysis_tool
    from . import find_similar_documents_tool
    from . import extract_entities_tool
except ImportError:
    # Tools may not be implemented yet
    pass

__all__ = [
    # Tool modules will be added here as they are implemented
]