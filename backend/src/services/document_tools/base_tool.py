"""Base class for all document processing tools"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from ..base_service import BaseService


class ToolCategory(str, Enum):
    """Categories for document tools"""
    ANALYSIS = "analysis"
    TRANSFORMATION = "transformation"
    VALIDATION = "validation"
    EXTRACTION = "extraction"
    SEARCH = "search"
    GENERATION = "generation"


class DocumentToolCategory(str, Enum):
    """Categories for document processing tools"""
    CONTENT_PROCESSING = "content_processing"
    DATA_VALIDATION = "data_validation"
    FORMAT_CONVERSION = "format_conversion"
    ANALYSIS = "analysis"
    ENHANCEMENT = "enhancement"
    SEARCH = "search"
    QUALITY = "quality"
    METADATA = "metadata"


class DocumentToolCapability(str, Enum):
    """Capabilities that document tools can provide"""
    VALIDATION = "validation"
    TRANSFORMATION = "transformation"
    ANALYSIS = "analysis"
    EXTRACTION = "extraction"
    ENHANCEMENT = "enhancement"
    SIMILARITY = "similarity"
    CLASSIFICATION = "classification"
    FORMATTING = "formatting"
    QUALITY_CHECK = "quality_check"
    METADATA_ENRICHMENT = "metadata_enrichment"


@dataclass
class DocumentToolMetadata:
    """Metadata about a document tool"""
    id: str
    name: str
    description: str
    category: DocumentToolCategory
    version: str = "1.0.0"
    icon: Optional[str] = None

    # Capabilities
    capabilities: List[DocumentToolCapability] = None

    # Document compatibility
    supported_document_types: List[Any] = None  # List of DocumentType enums
    min_content_length: Optional[int] = None
    max_content_length: Optional[int] = None

    # Execution info
    execution_time_estimate: str = "fast"  # "fast", "medium", "slow"
    requires_confirmation: bool = False
    batch_capable: bool = False

    # Service requirements
    requires_llm: bool = False
    requires_vector_search: bool = False
    requires_graph_db: bool = False

    # Schema
    input_schema: Dict[str, Any] = None
    output_schema: Dict[str, Any] = None

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
        if self.supported_document_types is None:
            self.supported_document_types = []
        if self.input_schema is None:
            self.input_schema = {}
        if self.output_schema is None:
            self.output_schema = {}


class BaseDocumentTool(ABC):
    """Abstract base class for all document processing tools

    This class defines the interface that all document tools must implement.
    Each tool encapsulates a specific document operation (validation, analysis, etc.)

    Tools receive services via dependency injection in the constructor.
    """

    def __init__(
        self,
        name: str,
        document_service: Any = None,
        llm_service: Any = None,
        vector_search_service: Any = None,
        graph_search_service: Any = None,
        **kwargs
    ):
        """Initialize the tool with service dependencies

        Args:
            name: Name of the tool
            document_service: Document service instance
            llm_service: LLM service instance
            vector_search_service: Vector search service instance
            graph_search_service: Graph search service instance
            **kwargs: Additional service dependencies
        """
        self.name = name
        self.document_service = document_service
        self.llm_service = llm_service
        self.vector_search_service = vector_search_service
        self.graph_search_service = graph_search_service
        self._services = kwargs

    @abstractmethod
    async def execute(
        self,
        document_id: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute the tool operation

        Args:
            document_id: ID of document to process
            parameters: Optional execution parameters

        Returns:
            Result of the tool operation

        Raises:
            ValueError: If input validation fails
            RuntimeError: If tool execution fails
        """
        pass

    @abstractmethod
    def get_metadata(self) -> DocumentToolMetadata:
        """Get tool metadata

        Returns:
            Tool metadata
        """
        pass

    def validate_input(
        self,
        document_id: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Validate input data against the tool's schema

        Args:
            document_id: Document ID to validate
            parameters: Parameters to validate

        Returns:
            True if valid, raises ValueError otherwise
        """
        metadata = self.get_metadata()

        if not document_id:
            raise ValueError("document_id is required")

        if parameters is None:
            parameters = {}

        # Check required fields
        for field, schema in metadata.input_schema.items():
            if schema.get("required", False) and field not in parameters:
                raise ValueError(f"Required parameter '{field}' missing")

            # Check field types if present
            if field in parameters and "type" in schema:
                expected_type = schema["type"]
                actual_value = parameters[field]

                type_map = {
                    "str": str,
                    "int": int,
                    "float": (int, float),
                    "bool": bool,
                    "list": list,
                    "dict": dict
                }

                expected_python_type = type_map.get(expected_type)
                if expected_python_type and not isinstance(actual_value, expected_python_type):
                    raise ValueError(
                        f"Parameter '{field}' must be {expected_type}, "
                        f"got {type(actual_value).__name__}"
                    )

        return True

    async def can_process_document(self, document_type: str, content_length: int = 0) -> bool:
        """Check if this tool can process the given document

        Args:
            document_type: Type of document
            content_length: Length of document content

        Returns:
            True if tool can process this document
        """
        metadata = self.get_metadata()

        # Check document type compatibility
        if metadata.supported_document_types and document_type not in metadata.supported_document_types:
            return False

        # Check content length constraints
        if metadata.min_content_length and content_length < metadata.min_content_length:
            return False
        if metadata.max_content_length and content_length > metadata.max_content_length:
            return False

        return True

    def get_recommendation_score(
        self,
        document_type: str,
        content_characteristics: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate recommendation score for this tool given document characteristics

        Args:
            document_type: Type of document
            content_characteristics: Optional content analysis results

        Returns:
            Score from 0.0 to 1.0
        """
        metadata = self.get_metadata()
        score = 0.0

        # Base score for document type compatibility
        if document_type in metadata.supported_document_types:
            score = 0.5

        # Override in subclasses for intelligent scoring
        return score

    def __str__(self) -> str:
        """String representation of the tool"""
        metadata = self.get_metadata()
        return f"{self.name} (v{metadata.version}): {metadata.description}"

    def __repr__(self) -> str:
        """Detailed representation of the tool"""
        return f"<{self.__class__.__name__}(name={self.name})>"
