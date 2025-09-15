"""Registry for LLM tools - manages tool registration and discovery"""

from typing import Dict, Type, Optional, List, Any
from enum import Enum

from .base_tool import BaseLLMTool, ToolMetadata, ToolCapability
from ...core.logger import CentralizedLogger


class LLMToolType(str, Enum):
    """Types of LLM tools available"""
    SUMMARIZATION = "summarization"
    MARKDOWN_FORMATTING = "markdown_formatting"
    ENTITY_EXTRACTION = "entity_extraction"
    CLASSIFICATION = "classification"
    LANGUAGE_DETECTION = "language_detection"
    QUESTION_ANSWERING = "question_answering"
    EMBEDDING = "embedding"
    TEXT_TO_MARKDOWN = "text_to_markdown"  # Alias for markdown formatting


class ToolRegistry:
    """Registry for managing LLM tools

    This class provides a central registry for all LLM tools,
    allowing dynamic registration and discovery of tools.
    """

    _tools: Dict[LLMToolType, Type[BaseLLMTool]] = {}
    _instances: Dict[LLMToolType, BaseLLMTool] = {}
    _logger = CentralizedLogger("ToolRegistry")

    @classmethod
    def register(cls, tool_type: LLMToolType, tool_class: Type[BaseLLMTool]):
        """Register a tool class

        Args:
            tool_type: Type identifier for the tool
            tool_class: Tool class to register
        """
        if not issubclass(tool_class, BaseLLMTool):
            raise ValueError(f"{tool_class} must inherit from BaseLLMTool")

        cls._tools[tool_type] = tool_class
        cls._logger.info(f"Registered LLM tool: {tool_type}")

    @classmethod
    def create(
        cls,
        tool_type: LLMToolType,
        llm_client: Any = None,
        singleton: bool = True,
        **kwargs
    ) -> BaseLLMTool:
        """Create or get a tool instance

        Args:
            tool_type: Type of tool to create
            llm_client: LLM client to use with the tool
            singleton: Whether to use singleton pattern
            **kwargs: Additional arguments for tool constructor

        Returns:
            Tool instance

        Raises:
            ValueError: If tool type is unknown
        """
        # Check for existing instance if singleton
        if singleton and tool_type in cls._instances:
            cls._logger.debug(f"Returning existing {tool_type} instance")
            return cls._instances[tool_type]

        # Create new instance
        tool_class = cls._tools.get(tool_type)
        if not tool_class:
            raise ValueError(f"Unknown tool type: {tool_type}")

        try:
            instance = tool_class(
                name=tool_type.value,
                llm_client=llm_client,
                **kwargs
            )

            # Store instance if singleton
            if singleton:
                cls._instances[tool_type] = instance

            cls._logger.info(f"Created {tool_type} tool instance")
            return instance

        except Exception as e:
            cls._logger.error(f"Failed to create {tool_type} tool: {str(e)}")
            raise

    @classmethod
    def get_all_tools(cls) -> Dict[LLMToolType, Type[BaseLLMTool]]:
        """Get all registered tool classes

        Returns:
            Dictionary of tool types to tool classes
        """
        return cls._tools.copy()

    @classmethod
    def get_tool_metadata(cls, tool_type: LLMToolType) -> Optional[ToolMetadata]:
        """Get metadata for a specific tool

        Args:
            tool_type: Type of tool

        Returns:
            Tool metadata or None if tool not found
        """
        tool_class = cls._tools.get(tool_type)
        if tool_class:
            # Create temporary instance to get metadata
            temp_instance = tool_class(name=tool_type.value)
            return temp_instance.get_metadata()
        return None

    @classmethod
    def find_tools_by_capability(
        cls,
        capability: ToolCapability
    ) -> List[LLMToolType]:
        """Find all tools with a specific capability

        Args:
            capability: Capability to search for

        Returns:
            List of tool types with the capability
        """
        matching_tools = []

        for tool_type in cls._tools:
            metadata = cls.get_tool_metadata(tool_type)
            if metadata and capability in metadata.capabilities:
                matching_tools.append(tool_type)

        return matching_tools

    @classmethod
    def get_available_tools(cls) -> List[LLMToolType]:
        """Get list of all available tool types

        Returns:
            List of registered tool types
        """
        return list(cls._tools.keys())

    @classmethod
    def clear_instances(cls):
        """Clear all singleton instances (mainly for testing)"""
        cls._instances.clear()
        cls._logger.info("Cleared all tool instances")

    @classmethod
    def is_registered(cls, tool_type: LLMToolType) -> bool:
        """Check if a tool type is registered

        Args:
            tool_type: Tool type to check

        Returns:
            True if registered, False otherwise
        """
        return tool_type in cls._tools

    @classmethod
    def get_tool_info(cls) -> Dict[str, Dict[str, Any]]:
        """Get information about all registered tools

        Returns:
            Dictionary with tool information
        """
        tool_info = {}

        for tool_type in cls._tools:
            metadata = cls.get_tool_metadata(tool_type)
            if metadata:
                tool_info[tool_type.value] = {
                    "name": metadata.name,
                    "description": metadata.description,
                    "version": metadata.version,
                    "capabilities": [cap.value for cap in metadata.capabilities],
                    "input_schema": metadata.input_schema,
                    "output_schema": metadata.output_schema,
                    "max_input_length": metadata.max_input_length,
                    "supports_streaming": metadata.supports_streaming
                }

        return tool_info