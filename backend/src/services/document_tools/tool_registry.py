"""Registry for document processing tools - manages tool registration and discovery"""

from typing import Dict, Type, Optional, List, Any, Set
from enum import Enum

from .base_tool import BaseDocumentTool, DocumentToolMetadata, DocumentToolCategory, DocumentToolCapability
from ...models.document import DocumentType, DocumentMessage
from ...core.logger import CentralizedLogger


class DocumentToolType(str, Enum):
    """Types of document tools available"""
    # JSON Tools
    VALIDATE_JSON = "validate_json"
    FORMAT_JSON = "format_json"
    EXTRACT_JSON_SCHEMA = "extract_json_schema"

    # Analysis Tools
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    EXTRACT_ENTITIES = "extract_entities"
    SUMMARIZE = "summarize"

    # Search Tools
    FIND_SIMILAR_DOCUMENTS = "find_similar_documents"

    # Quality Tools
    CHECK_GRAMMAR = "check_grammar"
    DETECT_LANGUAGE = "detect_language"

    # Enhancement Tools
    ENRICH_METADATA = "enrich_metadata"
    GENERATE_TAGS = "generate_tags"

    # Transformation Tools
    CONVERT_FORMAT = "convert_format"
    EXTRACT_TEXT = "extract_text"


class DocumentToolRegistry:
    """Registry for managing document processing tools

    This class provides a central registry for all document tools,
    allowing dynamic registration and discovery of tools based on
    document type, capabilities, and categories.
    """

    _tools: Dict[DocumentToolType, Type[BaseDocumentTool]] = {}
    _instances: Dict[DocumentToolType, BaseDocumentTool] = {}
    _logger = CentralizedLogger("DocumentToolRegistry")

    @classmethod
    def register(cls, tool_type: DocumentToolType, tool_class: Type[BaseDocumentTool]):
        """Register a tool class

        Args:
            tool_type: Type identifier for the tool
            tool_class: Tool class to register
        """
        if not issubclass(tool_class, BaseDocumentTool):
            raise ValueError(f"{tool_class} must inherit from BaseDocumentTool")

        cls._tools[tool_type] = tool_class
        cls._logger.info(f"Registered document tool: {tool_type}")

    @classmethod
    def create(
        cls,
        tool_type: DocumentToolType,
        document_service: Optional[Any] = None,
        llm_service: Optional[Any] = None,
        vector_search_service: Optional[Any] = None,
        singleton: bool = True,
        **kwargs
    ) -> BaseDocumentTool:
        """Create or get a tool instance

        Args:
            tool_type: Type of tool to create
            document_service: Document service for DI
            llm_service: LLM service for DI
            vector_search_service: Vector search service for DI
            singleton: Whether to use singleton pattern
            **kwargs: Additional service dependencies

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
                tool_id=tool_type.value,
                document_service=document_service,
                llm_service=llm_service,
                vector_search_service=vector_search_service,
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
    def get_all_tools(cls) -> Dict[DocumentToolType, Type[BaseDocumentTool]]:
        """Get all registered tool classes

        Returns:
            Dictionary of tool types to tool classes
        """
        return cls._tools.copy()

    @classmethod
    def get_tool_metadata(cls, tool_type: DocumentToolType) -> Optional[DocumentToolMetadata]:
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
    def find_tools_by_document_type(
        cls,
        document_type: DocumentType
    ) -> List[DocumentToolType]:
        """Find all tools that support a specific document type

        Args:
            document_type: Document type to search for

        Returns:
            List of tool types supporting the document type
        """
        matching_tools = []

        for tool_type in cls._tools:
            metadata = cls.get_tool_metadata(tool_type)
            if metadata and (
                not metadata.supported_document_types or  # Empty means all types
                document_type in metadata.supported_document_types
            ):
                matching_tools.append(tool_type)

        return matching_tools

    @classmethod
    def find_tools_by_capability(
        cls,
        capability: DocumentToolCapability
    ) -> List[DocumentToolType]:
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
    def find_tools_by_category(
        cls,
        category: DocumentToolCategory
    ) -> List[DocumentToolType]:
        """Find all tools in a specific category

        Args:
            category: Category to search for

        Returns:
            List of tool types in the category
        """
        matching_tools = []

        for tool_type in cls._tools:
            metadata = cls.get_tool_metadata(tool_type)
            if metadata and metadata.category == category:
                matching_tools.append(tool_type)

        return matching_tools

    @classmethod
    def get_recommendations_for_document(
        cls,
        document: DocumentMessage,
        document_service: Optional[Any] = None,
        llm_service: Optional[Any] = None,
        vector_search_service: Optional[Any] = None,
        max_recommendations: int = 5
    ) -> List[Dict[str, Any]]:
        """Get tool recommendations for a specific document

        Args:
            document: Document to get recommendations for
            document_service: Document service for tool creation
            llm_service: LLM service for tool creation
            vector_search_service: Vector search service for tool creation
            max_recommendations: Maximum number of recommendations

        Returns:
            List of tool recommendations with scores
        """
        recommendations = []

        for tool_type in cls._tools:
            try:
                # Create tool instance to get recommendations
                tool = cls.create(
                    tool_type,
                    document_service=document_service,
                    llm_service=llm_service,
                    vector_search_service=vector_search_service,
                    singleton=False  # Don't cache these temporary instances
                )

                recommendation = tool.get_recommendations_for_document(document)

                if recommendation["applicable"]:
                    recommendations.append({
                        "tool_type": tool_type.value,
                        "tool_name": tool.get_metadata().name,
                        "tool_icon": tool.get_metadata().icon,
                        "tool_category": tool.get_metadata().category.value,
                        **recommendation
                    })

            except Exception as e:
                cls._logger.warning(f"Failed to get recommendation from {tool_type}: {str(e)}")

        # Sort by score descending
        recommendations.sort(key=lambda x: x["score"], reverse=True)

        return recommendations[:max_recommendations]

    @classmethod
    def get_available_tools(cls) -> List[DocumentToolType]:
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
    def is_registered(cls, tool_type: DocumentToolType) -> bool:
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
            Dictionary with tool information organized by category
        """
        tool_info = {
            "categories": {},
            "tools": {}
        }

        # Group tools by category
        for tool_type in cls._tools:
            metadata = cls.get_tool_metadata(tool_type)
            if metadata:
                category_name = metadata.category.value

                # Initialize category if not exists
                if category_name not in tool_info["categories"]:
                    tool_info["categories"][category_name] = {
                        "name": category_name,
                        "tools": []
                    }

                # Add tool to category
                tool_data = {
                    "id": metadata.id,
                    "name": metadata.name,
                    "description": metadata.description,
                    "icon": metadata.icon,
                    "version": metadata.version,
                    "capabilities": [cap.value for cap in metadata.capabilities],
                    "supported_document_types": [dt.value for dt in metadata.supported_document_types],
                    "execution_time_estimate": metadata.execution_time_estimate,
                    "batch_capable": metadata.batch_capable,
                    "requires_llm": metadata.requires_llm,
                    "requires_vector_search": metadata.requires_vector_search
                }

                tool_info["categories"][category_name]["tools"].append(tool_data)
                tool_info["tools"][metadata.id] = tool_data

        return tool_info

    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """Get registry statistics

        Returns:
            Statistics about registered tools
        """
        total_tools = len(cls._tools)
        active_instances = len(cls._instances)

        # Count by category
        category_counts = {}
        capability_counts = {}
        document_type_support = {}

        for tool_type in cls._tools:
            metadata = cls.get_tool_metadata(tool_type)
            if metadata:
                # Count categories
                category = metadata.category.value
                category_counts[category] = category_counts.get(category, 0) + 1

                # Count capabilities
                for capability in metadata.capabilities:
                    cap_name = capability.value
                    capability_counts[cap_name] = capability_counts.get(cap_name, 0) + 1

                # Count document type support
                for doc_type in metadata.supported_document_types:
                    dt_name = doc_type.value
                    document_type_support[dt_name] = document_type_support.get(dt_name, 0) + 1

        return {
            "total_tools": total_tools,
            "active_instances": active_instances,
            "category_distribution": category_counts,
            "capability_distribution": capability_counts,
            "document_type_support": document_type_support
        }