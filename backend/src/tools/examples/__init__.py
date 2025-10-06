"""Example tool implementations demonstrating the unified tool system

All tools in this module are automatically discovered and registered via the
@register_tool decorator. No manual imports or registration required.
"""

from ..tool_decorators import auto_discover_tools

# Auto-discover and register all tools in this package
__all__ = []


# This will automatically import all tool modules and register decorated tools
def load_example_tools():
    """Load all example tools via auto-discovery"""
    return auto_discover_tools(["src.tools.examples"])
