"""Base classes for generic tool system"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ToolCategory(str, Enum):
    """High-level categories for tools"""

    # Processing categories
    ANALYSIS = "analysis"
    TRANSFORMATION = "transformation"
    GENERATION = "generation"
    VALIDATION = "validation"
    EXTRACTION = "extraction"

    # Integration categories
    SEARCH = "search"
    STORAGE = "storage"
    COMMUNICATION = "communication"
    COMPUTATION = "computation"

    # AI/ML categories
    LLM = "llm"
    EMBEDDING = "embedding"
    CLASSIFICATION = "classification"


class ToolCapability(str, Enum):
    """Specific capabilities tools can provide"""

    # Text capabilities
    TEXT_ANALYSIS = "text_analysis"
    TEXT_GENERATION = "text_generation"
    TEXT_TRANSFORMATION = "text_transformation"
    LANGUAGE_DETECTION = "language_detection"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"

    # Data capabilities
    DATA_EXTRACTION = "data_extraction"
    DATA_VALIDATION = "data_validation"
    DATA_FORMATTING = "data_formatting"
    SCHEMA_GENERATION = "schema_generation"

    # Search capabilities
    SEMANTIC_SEARCH = "semantic_search"
    VECTOR_SEARCH = "vector_search"
    FULLTEXT_SEARCH = "fulltext_search"
    SIMILARITY = "similarity"

    # AI/ML capabilities
    ENTITY_RECOGNITION = "entity_recognition"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    CLASSIFICATION = "classification"
    EMBEDDING_GENERATION = "embedding_generation"
    QUESTION_ANSWERING = "question_answering"

    # Utility capabilities
    FORMAT_CONVERSION = "format_conversion"
    QUALITY_CHECK = "quality_check"
    METADATA_ENRICHMENT = "metadata_enrichment"


class ToolType(str, Enum):
    """Types of tool implementations"""

    LLM = "llm"  # LLM-based tools (OpenAI, Anthropic, etc.)
    MCP = "mcp"  # MCP server tools
    EXECUTABLE = "executable"  # Python scripts, binaries
    DOCUMENT = "document"  # Document processing tools
    HYBRID = "hybrid"  # Combination of multiple types


@dataclass
class ToolExecutionContext:
    """Context passed to tools during execution"""

    user_id: Optional[str] = None
    session_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolMetadata:
    """Comprehensive metadata about a tool"""

    # Identification
    id: str
    name: str
    description: str
    version: str = "1.0.0"
    author: Optional[str] = None

    # Categorization
    category: ToolCategory = ToolCategory.COMPUTATION
    capabilities: List[ToolCapability] = field(default_factory=list)
    tool_type: ToolType = ToolType.EXECUTABLE

    # Schema
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)

    # Execution characteristics
    execution_time_estimate: str = "fast"  # fast, medium, slow
    max_input_length: Optional[int] = None
    supports_streaming: bool = False
    supports_batch: bool = False
    is_async: bool = True

    # Requirements
    requires_api_key: bool = False
    requires_llm: bool = False
    requires_mcp: bool = False
    requires_vector_db: bool = False
    requires_graph_db: bool = False

    # UI/UX
    icon: Optional[str] = None
    requires_confirmation: bool = False

    # Documentation
    examples: List[Dict[str, Any]] = field(default_factory=list)
    documentation_url: Optional[str] = None

    def __post_init__(self):
        """Validate and normalize metadata"""
        if not self.capabilities:
            self.capabilities = []
        if not self.input_schema:
            self.input_schema = {}
        if not self.output_schema:
            self.output_schema = {}
        if not self.examples:
            self.examples = []


class BaseTool(ABC):
    """Abstract base class for all tools in the system

    This unified interface supports:
    - LLM-based tools
    - MCP server tools
    - Executable Python programs
    - Document processing tools

    All tools must implement:
    1. get_metadata() - Return tool metadata
    2. execute() - Async execution method
    3. validate_input() - Input validation
    """

    def __init__(
        self,
        name: str,
        llm_service: Optional[Any] = None,
        document_service: Optional[Any] = None,
        vector_search_service: Optional[Any] = None,
        mcp_service: Optional[Any] = None,
        storage: Optional[Any] = None,
        **kwargs,
    ):
        """Initialize the tool with dependency injection

        Args:
            name: Unique tool name/identifier
            llm_service: Optional LLM service for AI operations
            document_service: Optional document service for document operations
            vector_search_service: Optional vector search service for semantic search
            mcp_service: Optional MCP service for MCP tool operations
            storage: Optional storage adapter for data persistence
            **kwargs: Tool-specific configuration
        """
        self.name = name
        self.llm_service = llm_service
        self.document_service = document_service
        self.vector_search_service = vector_search_service
        self.mcp_service = mcp_service
        self.storage = storage
        self._config = kwargs
        self._metadata: Optional[ToolMetadata] = None

    @abstractmethod
    async def execute(
        self, input_data: Dict[str, Any], context: Optional[ToolExecutionContext] = None
    ) -> Dict[str, Any]:
        """Execute the tool operation

        Args:
            input_data: Input parameters for the tool
            context: Execution context (user, session, trace info)

        Returns:
            Result dictionary matching output_schema

        Raises:
            ValueError: If input validation fails
            RuntimeError: If tool execution fails
        """
        pass

    @abstractmethod
    def get_metadata(self) -> ToolMetadata:
        """Get comprehensive tool metadata

        Returns:
            Tool metadata with capabilities, schemas, requirements
        """
        pass

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data against tool's input schema

        Args:
            input_data: Input data to validate

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        metadata = self.get_metadata()

        # Check required fields
        for field_name, schema in metadata.input_schema.items():
            if schema.get("required", False) and field_name not in input_data:
                raise ValueError(f"Required field '{field_name}' missing")

            # Type validation
            if field_name in input_data and "type" in schema:
                expected_type = schema["type"]
                actual_value = input_data[field_name]

                type_validators = {
                    "str": lambda v: isinstance(v, str),
                    "int": lambda v: isinstance(v, int),
                    "float": lambda v: isinstance(v, (int, float)),
                    "bool": lambda v: isinstance(v, bool),
                    "list": lambda v: isinstance(v, list),
                    "dict": lambda v: isinstance(v, dict),
                }

                validator = type_validators.get(expected_type)
                if validator and not validator(actual_value):
                    raise ValueError(
                        f"Field '{field_name}' must be {expected_type}, "
                        f"got {type(actual_value).__name__}"
                    )

        # Check max input length if specified
        if metadata.max_input_length:
            for field_name in ["text", "content", "input"]:
                if field_name in input_data:
                    text_length = len(input_data[field_name])
                    if text_length > metadata.max_input_length:
                        raise ValueError(
                            f"Input exceeds maximum length of "
                            f"{metadata.max_input_length} characters"
                        )

        return True

    async def can_execute(
        self, input_data: Dict[str, Any], context: Optional[ToolExecutionContext] = None
    ) -> bool:
        """Check if tool can execute with given input

        Args:
            input_data: Input data to check
            context: Execution context

        Returns:
            True if tool can execute
        """
        try:
            self.validate_input(input_data)
            return True
        except (ValueError, RuntimeError):
            return False

    def get_example_usage(self) -> List[Dict[str, Any]]:
        """Get example usage scenarios

        Returns:
            List of example input/output pairs
        """
        metadata = self.get_metadata()
        return metadata.examples

    def __str__(self) -> str:
        """String representation"""
        metadata = self.get_metadata()
        return f"{metadata.name} (v{metadata.version}): {metadata.description}"

    def __repr__(self) -> str:
        """Detailed representation"""
        metadata = self.get_metadata()
        return (
            f"<{self.__class__.__name__}"
            f"(name={metadata.name}, "
            f"type={metadata.tool_type.value}, "
            f"category={metadata.category.value})>"
        )
