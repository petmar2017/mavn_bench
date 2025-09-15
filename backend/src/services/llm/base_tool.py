"""Base class for all LLM tools"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from ..base_service import BaseService


class ToolCapability(str, Enum):
    """Types of capabilities a tool can have"""
    TEXT_GENERATION = "text_generation"
    TEXT_ANALYSIS = "text_analysis"
    TEXT_TRANSFORMATION = "text_transformation"
    EMBEDDING_GENERATION = "embedding_generation"
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"
    QUESTION_ANSWERING = "question_answering"


@dataclass
class ToolMetadata:
    """Metadata about an LLM tool"""
    name: str
    description: str
    version: str = "1.0.0"
    capabilities: List[ToolCapability] = None
    input_schema: Dict[str, Any] = None
    output_schema: Dict[str, Any] = None
    max_input_length: Optional[int] = None
    supports_streaming: bool = False
    requires_api_key: bool = True

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
        if self.input_schema is None:
            self.input_schema = {}
        if self.output_schema is None:
            self.output_schema = {}


class BaseLLMTool(ABC):
    """Abstract base class for all LLM tools

    This class defines the interface that all LLM tools must implement.
    Each tool encapsulates a specific LLM operation (summarization, extraction, etc.)
    """

    def __init__(self, name: str, llm_client: Any = None):
        """Initialize the tool

        Args:
            name: Name of the tool
            llm_client: LLM client instance (OpenAI, Anthropic, etc.)
        """
        self.name = name
        self.llm_client = llm_client
        self._metadata = None

    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool operation

        Args:
            input_data: Input data for the tool operation

        Returns:
            Result of the tool operation

        Raises:
            ValueError: If input validation fails
            RuntimeError: If tool execution fails
        """
        pass

    @abstractmethod
    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata including capabilities and schemas

        Returns:
            Tool metadata
        """
        pass

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input data against the tool's input schema

        Args:
            input_data: Input data to validate

        Returns:
            True if valid, raises ValueError otherwise
        """
        metadata = self.get_metadata()

        # Check required fields
        for field, schema in metadata.input_schema.items():
            if schema.get("required", False) and field not in input_data:
                raise ValueError(f"Required field '{field}' missing")

            # Check field types if present
            if field in input_data and "type" in schema:
                expected_type = schema["type"]
                actual_value = input_data[field]

                if expected_type == "str" and not isinstance(actual_value, str):
                    raise ValueError(f"Field '{field}' must be a string")
                elif expected_type == "int" and not isinstance(actual_value, int):
                    raise ValueError(f"Field '{field}' must be an integer")
                elif expected_type == "float" and not isinstance(actual_value, (int, float)):
                    raise ValueError(f"Field '{field}' must be a number")
                elif expected_type == "bool" and not isinstance(actual_value, bool):
                    raise ValueError(f"Field '{field}' must be a boolean")
                elif expected_type == "list" and not isinstance(actual_value, list):
                    raise ValueError(f"Field '{field}' must be a list")
                elif expected_type == "dict" and not isinstance(actual_value, dict):
                    raise ValueError(f"Field '{field}' must be a dictionary")

        # Check max input length if specified
        if metadata.max_input_length and "text" in input_data:
            text_length = len(input_data["text"])
            if text_length > metadata.max_input_length:
                raise ValueError(f"Input text exceeds maximum length of {metadata.max_input_length} characters")

        return True

    def prepare_prompt(self, template: str, **kwargs) -> str:
        """Prepare a prompt from a template

        Args:
            template: Prompt template with placeholders
            **kwargs: Values to fill in the template

        Returns:
            Formatted prompt
        """
        return template.format(**kwargs)

    async def call_llm(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """Call the LLM with the given prompt

        Args:
            prompt: Prompt to send to the LLM
            max_tokens: Maximum tokens in response
            temperature: Temperature for generation
            **kwargs: Additional parameters for the LLM

        Returns:
            LLM response text
        """
        if not self.llm_client:
            raise RuntimeError("LLM client not configured")

        # This will be implemented by the LLMService
        return await self.llm_client.generate(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )

    def __str__(self) -> str:
        """String representation of the tool"""
        metadata = self.get_metadata()
        return f"{self.name} (v{metadata.version}): {metadata.description}"

    def __repr__(self) -> str:
        """Detailed representation of the tool"""
        return f"<{self.__class__.__name__}(name={self.name})>"