"""Unified tool registry for all tool types"""

from enum import Enum
from typing import Any, Dict, List, Optional, Set, Type

from ..core.logger import CentralizedLogger
from .base_tool import (BaseTool, ToolCapability, ToolCategory, ToolMetadata,
                        ToolType)


class ToolRegistry:
    """Central registry for all tools in the system

    Manages registration, discovery, and creation of tools across
    all types: LLM, MCP, Executable, and Document processing tools.

    Features:
    - Auto-registration via decorators
    - Category and capability-based discovery
    - Singleton pattern support
    - Tool recommendation system
    - Statistics and monitoring
    """

    _tools: Dict[str, Type[BaseTool]] = {}
    _instances: Dict[str, BaseTool] = {}
    _logger = CentralizedLogger("ToolRegistry")

    # Index structures for fast lookups
    _by_category: Dict[ToolCategory, Set[str]] = {}
    _by_capability: Dict[ToolCapability, Set[str]] = {}
    _by_type: Dict[ToolType, Set[str]] = {}

    @classmethod
    def register(cls, tool_id: str, tool_class: Type[BaseTool]):
        """Register a tool class

        Args:
            tool_id: Unique identifier for the tool
            tool_class: Tool class to register

        Raises:
            ValueError: If tool doesn't inherit from BaseTool
        """
        if not issubclass(tool_class, BaseTool):
            raise ValueError(f"{tool_class} must inherit from BaseTool")

        # Store tool class
        cls._tools[tool_id] = tool_class

        # Update indexes
        try:
            # Create temporary instance to get metadata
            temp_instance = tool_class(name=tool_id)
            metadata = temp_instance.get_metadata()

            # Index by category
            if metadata.category not in cls._by_category:
                cls._by_category[metadata.category] = set()
            cls._by_category[metadata.category].add(tool_id)

            # Index by capabilities
            for capability in metadata.capabilities:
                if capability not in cls._by_capability:
                    cls._by_capability[capability] = set()
                cls._by_capability[capability].add(tool_id)

            # Index by type
            if metadata.tool_type not in cls._by_type:
                cls._by_type[metadata.tool_type] = set()
            cls._by_type[metadata.tool_type].add(tool_id)

            cls._logger.info(
                f"Registered tool: {tool_id} "
                f"(type={metadata.tool_type.value}, "
                f"category={metadata.category.value})"
            )

        except Exception as e:
            cls._logger.warning(
                f"Could not index tool {tool_id} during registration: {str(e)}"
            )

    @classmethod
    def create(cls, tool_id: str, singleton: bool = True, **kwargs) -> BaseTool:
        """Create or get a tool instance

        Args:
            tool_id: ID of tool to create
            singleton: Whether to use singleton pattern
            **kwargs: Tool-specific configuration

        Returns:
            Tool instance

        Raises:
            ValueError: If tool ID is unknown
        """
        # Check for existing instance if singleton
        if singleton and tool_id in cls._instances:
            cls._logger.debug(f"Returning existing {tool_id} instance")
            return cls._instances[tool_id]

        # Get tool class
        tool_class = cls._tools.get(tool_id)
        if not tool_class:
            raise ValueError(f"Unknown tool ID: {tool_id}")

        try:
            # Create instance
            instance = tool_class(name=tool_id, **kwargs)

            # Store if singleton
            if singleton:
                cls._instances[tool_id] = instance

            cls._logger.info(f"Created {tool_id} tool instance (singleton={singleton})")
            return instance

        except Exception as e:
            cls._logger.error(f"Failed to create {tool_id} tool: {str(e)}")
            raise

    @classmethod
    def get_all_tools(cls) -> Dict[str, Type[BaseTool]]:
        """Get all registered tool classes

        Returns:
            Dictionary mapping tool IDs to tool classes
        """
        return cls._tools.copy()

    @classmethod
    def get_tool_metadata(cls, tool_id: str) -> Optional[ToolMetadata]:
        """Get metadata for a specific tool

        Args:
            tool_id: Tool identifier

        Returns:
            Tool metadata or None if not found
        """
        tool_class = cls._tools.get(tool_id)
        if tool_class:
            try:
                temp_instance = tool_class(name=tool_id)
                return temp_instance.get_metadata()
            except Exception as e:
                cls._logger.error(f"Failed to get metadata for {tool_id}: {str(e)}")
        return None

    @classmethod
    def find_tools_by_category(cls, category: ToolCategory) -> List[str]:
        """Find all tools in a specific category

        Args:
            category: Category to search for

        Returns:
            List of tool IDs in the category
        """
        return list(cls._by_category.get(category, set()))

    @classmethod
    def find_tools_by_capability(cls, capability: ToolCapability) -> List[str]:
        """Find all tools with a specific capability

        Args:
            capability: Capability to search for

        Returns:
            List of tool IDs with the capability
        """
        return list(cls._by_capability.get(capability, set()))

    @classmethod
    def find_tools_by_type(cls, tool_type: ToolType) -> List[str]:
        """Find all tools of a specific type

        Args:
            tool_type: Tool type to search for

        Returns:
            List of tool IDs of the type
        """
        return list(cls._by_type.get(tool_type, set()))

    @classmethod
    def find_tools_by_criteria(
        cls,
        category: Optional[ToolCategory] = None,
        capabilities: Optional[List[ToolCapability]] = None,
        tool_type: Optional[ToolType] = None,
        requires_llm: Optional[bool] = None,
        requires_mcp: Optional[bool] = None,
    ) -> List[str]:
        """Find tools matching multiple criteria

        Args:
            category: Filter by category
            capabilities: Filter by capabilities (tool must have ALL)
            tool_type: Filter by tool type
            requires_llm: Filter by LLM requirement
            requires_mcp: Filter by MCP requirement

        Returns:
            List of matching tool IDs
        """
        # Start with all tools
        candidates = set(cls._tools.keys())

        # Apply category filter
        if category is not None:
            candidates &= cls._by_category.get(category, set())

        # Apply type filter
        if tool_type is not None:
            candidates &= cls._by_type.get(tool_type, set())

        # Apply capability filters
        if capabilities:
            for capability in capabilities:
                candidates &= cls._by_capability.get(capability, set())

        # Apply requirement filters
        if requires_llm is not None or requires_mcp is not None:
            filtered = set()
            for tool_id in candidates:
                metadata = cls.get_tool_metadata(tool_id)
                if metadata:
                    if (
                        requires_llm is not None
                        and metadata.requires_llm != requires_llm
                    ):
                        continue
                    if (
                        requires_mcp is not None
                        and metadata.requires_mcp != requires_mcp
                    ):
                        continue
                    filtered.add(tool_id)
            candidates = filtered

        return list(candidates)

    @classmethod
    def get_available_tools(cls) -> List[str]:
        """Get list of all available tool IDs

        Returns:
            List of registered tool IDs
        """
        return list(cls._tools.keys())

    @classmethod
    def clear_instances(cls):
        """Clear all singleton instances (mainly for testing)"""
        cls._instances.clear()
        cls._logger.info("Cleared all tool instances")

    @classmethod
    def is_registered(cls, tool_id: str) -> bool:
        """Check if a tool ID is registered

        Args:
            tool_id: Tool ID to check

        Returns:
            True if registered, False otherwise
        """
        return tool_id in cls._tools

    @classmethod
    def get_tool_info(cls) -> Dict[str, Any]:
        """Get comprehensive information about all registered tools

        Returns:
            Dictionary with organized tool information
        """
        info = {
            "total_tools": len(cls._tools),
            "by_category": {},
            "by_type": {},
            "by_capability": {},
            "tools": {},
        }

        # Organize by category
        for category, tool_ids in cls._by_category.items():
            info["by_category"][category.value] = {
                "count": len(tool_ids),
                "tools": list(tool_ids),
            }

        # Organize by type
        for tool_type, tool_ids in cls._by_type.items():
            info["by_type"][tool_type.value] = {
                "count": len(tool_ids),
                "tools": list(tool_ids),
            }

        # Organize by capability
        for capability, tool_ids in cls._by_capability.items():
            info["by_capability"][capability.value] = {
                "count": len(tool_ids),
                "tools": list(tool_ids),
            }

        # Detailed tool information
        for tool_id in cls._tools:
            metadata = cls.get_tool_metadata(tool_id)
            if metadata:
                info["tools"][tool_id] = {
                    "name": metadata.name,
                    "description": metadata.description,
                    "version": metadata.version,
                    "category": metadata.category.value,
                    "type": metadata.tool_type.value,
                    "capabilities": [cap.value for cap in metadata.capabilities],
                    "execution_time": metadata.execution_time_estimate,
                    "supports_streaming": metadata.supports_streaming,
                    "supports_batch": metadata.supports_batch,
                    "requires_llm": metadata.requires_llm,
                    "requires_mcp": metadata.requires_mcp,
                    "icon": metadata.icon,
                }

        return info

    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """Get registry statistics

        Returns:
            Statistics about registered tools
        """
        return {
            "total_tools": len(cls._tools),
            "active_instances": len(cls._instances),
            "categories": {
                cat.value: len(tools) for cat, tools in cls._by_category.items()
            },
            "types": {typ.value: len(tools) for typ, tools in cls._by_type.items()},
            "top_capabilities": sorted(
                [(cap.value, len(tools)) for cap, tools in cls._by_capability.items()],
                key=lambda x: x[1],
                reverse=True,
            )[:10],
        }

    @classmethod
    def rebuild_indexes(cls):
        """Rebuild all indexes from registered tools

        Useful after bulk registration or updates
        """
        cls._by_category.clear()
        cls._by_capability.clear()
        cls._by_type.clear()

        for tool_id in cls._tools:
            metadata = cls.get_tool_metadata(tool_id)
            if metadata:
                # Index by category
                if metadata.category not in cls._by_category:
                    cls._by_category[metadata.category] = set()
                cls._by_category[metadata.category].add(tool_id)

                # Index by capabilities
                for capability in metadata.capabilities:
                    if capability not in cls._by_capability:
                        cls._by_capability[capability] = set()
                    cls._by_capability[capability].add(tool_id)

                # Index by type
                if metadata.tool_type not in cls._by_type:
                    cls._by_type[metadata.tool_type] = set()
                cls._by_type[metadata.tool_type].add(tool_id)

        cls._logger.info("Rebuilt tool indexes")
