"""LLM service for AI operations using tool-based architecture"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum

from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from .base_service import BaseService
from .service_factory import ServiceFactory, ServiceType
from .llm.tool_registry import ToolRegistry, LLMToolType
from .llm.base_tool import BaseLLMTool, ToolCapability
from ..models.document import DocumentMessage, DocumentType
from ..core.config import get_settings


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


class LLMClient:
    """Wrapper for LLM API clients to provide unified interface for tools"""

    def __init__(
        self,
        provider: LLMProvider,
        openai_client: Optional[AsyncOpenAI] = None,
        anthropic_client: Optional[AsyncAnthropic] = None,
        model: str = None,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ):
        self.provider = provider
        self.openai_client = openai_client
        self.anthropic_client = anthropic_client
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """Generate text using the appropriate LLM provider"""
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature

        if self.provider == LLMProvider.ANTHROPIC and self.anthropic_client:
            response = await self.anthropic_client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text

        elif self.provider == LLMProvider.OPENAI and self.openai_client:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content

        else:
            # Fallback for testing
            await asyncio.sleep(0.1)  # Simulate API latency
            return f"Generated response for: {prompt[:100]}..."

    async def generate_embeddings(
        self,
        text: str,
        model: str = "text-embedding-ada-002"
    ) -> List[float]:
        """Generate embeddings (OpenAI only for now)"""
        if self.openai_client:
            response = await self.openai_client.embeddings.create(
                model=model,
                input=text
            )
            return response.data[0].embedding
        else:
            # Mock embeddings for testing
            import random
            return [random.random() for _ in range(384)]


class LLMService(BaseService):
    """Service for LLM operations using tool-based architecture

    This refactored service uses a modular tool-based approach where each
    AI operation is encapsulated in its own tool class. This provides:
    - Better modularity and maintainability
    - Easier testing and extension
    - Plugin-like architecture for adding new capabilities
    """

    def __init__(self, provider: Optional[LLMProvider] = None):
        """Initialize LLM service

        Args:
            provider: LLM provider to use (defaults to config)
        """
        super().__init__("LLMService")
        settings = get_settings()

        # Use provider from argument or default from config
        if provider is None:
            provider = LLMProvider.ANTHROPIC if settings.llm.default_provider == "anthropic" else LLMProvider.OPENAI

        self.provider = provider

        # Set provider-specific settings
        if provider == LLMProvider.ANTHROPIC:
            max_tokens = settings.llm.claude_max_tokens
            temperature = settings.llm.claude_temperature
            model = settings.llm.claude_model
        elif provider == LLMProvider.OPENAI:
            max_tokens = settings.llm.openai_max_tokens
            temperature = settings.llm.openai_temperature
            model = settings.llm.openai_model
        else:
            max_tokens = settings.llm.max_tokens
            temperature = settings.llm.temperature
            model = settings.llm.default_model

        # Initialize API clients
        openai_client = None
        anthropic_client = None

        if settings.llm.openai_api_key:
            openai_client = AsyncOpenAI(api_key=settings.llm.openai_api_key)

        if settings.llm.anthropic_api_key:
            anthropic_client = AsyncAnthropic(api_key=settings.llm.anthropic_api_key)

        # Create LLM client wrapper for tools
        self.llm_client = LLMClient(
            provider=provider,
            openai_client=openai_client,
            anthropic_client=anthropic_client,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature
        )

        # Register all tools on first initialization
        self._register_tools()

        self.logger.info(f"Initialized LLMService with provider: {provider} using tool-based architecture")

    def _register_tools(self):
        """Register all available LLM tools using auto-discovery"""
        try:
            # Import all tool modules to trigger decorator registration
            # This import will execute the @register_tool decorators
            from .llm import tools  # noqa: F401

            # Auto-register all decorated tools
            from .llm.tool_decorators import auto_register_decorated_tools

            # Register all tools that were decorated
            num_registered = auto_register_decorated_tools()

            self.logger.info(f"Auto-registered {num_registered} LLM tools via decorators")

            # Log available tools for debugging
            available_tools = ToolRegistry.get_available_tools()
            self.logger.debug(f"Available tools: {[tool.value for tool in available_tools]}")

        except ImportError as e:
            self.logger.error(f"Failed to import tools: {str(e)}")
            raise RuntimeError(f"Tool registration failed: {str(e)}")

    async def execute_tool(
        self,
        tool_type: LLMToolType,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a specific tool

        Args:
            tool_type: Type of tool to execute
            input_data: Input data for the tool

        Returns:
            Tool execution result
        """
        with self.traced_operation(
            "execute_tool",
            tool_type=tool_type.value,
            input_keys=list(input_data.keys())
        ):
            try:
                # Get or create tool instance
                tool = ToolRegistry.create(
                    tool_type=tool_type,
                    llm_client=self.llm_client,
                    singleton=True
                )

                # Execute tool
                result = await tool.execute(input_data)

                self.logger.info(f"Executed tool {tool_type.value} successfully")
                return result

            except Exception as e:
                self.logger.error(f"Failed to execute tool {tool_type.value}: {str(e)}")
                raise

    # Backwards compatibility methods
    # These methods maintain the same interface as the old service
    # but delegate to the appropriate tools

    async def text_to_markdown(
        self,
        text: str,
        preserve_structure: bool = True
    ) -> str:
        """Convert plain text to well-formatted markdown

        Args:
            text: Plain text to convert
            preserve_structure: Whether to preserve original structure

        Returns:
            Formatted markdown text
        """
        result = await self.execute_tool(
            LLMToolType.TEXT_TO_MARKDOWN,
            {
                "text": text,
                "preserve_structure": preserve_structure
            }
        )
        return result.get("markdown", text)

    async def generate_summary(
        self,
        text: str,
        max_length: int = 500,
        style: str = "concise"
    ) -> str:
        """Generate a summary of the provided text

        Args:
            text: Text to summarize
            max_length: Maximum length of summary in words
            style: Summary style (concise, detailed, bullet_points)

        Returns:
            Generated summary
        """
        result = await self.execute_tool(
            LLMToolType.SUMMARIZATION,
            {
                "text": text,
                "max_length": max_length,
                "style": style
            }
        )
        return result.get("summary", "")

    async def extract_entities(
        self,
        text: str,
        entity_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Extract named entities from text

        Args:
            text: Text to extract entities from
            entity_types: Specific entity types to extract

        Returns:
            List of extracted entities
        """
        result = await self.execute_tool(
            LLMToolType.ENTITY_EXTRACTION,
            {
                "text": text,
                "entity_types": entity_types
            }
        )

        # Convert to old Entity format for compatibility
        entities = result.get("entities", [])

        # Create Entity-like dictionaries
        entity_objects = []
        for entity_dict in entities:
            # The tool already returns dictionaries with the right format
            entity_objects.append(entity_dict)

        return entity_objects

    async def classify_document(
        self,
        text: str,
        categories: Optional[List[str]] = None
    ) -> Tuple[str, float]:
        """Classify document into categories

        Args:
            text: Document text to classify
            categories: Possible categories

        Returns:
            Tuple of (category, confidence)
        """
        result = await self.execute_tool(
            LLMToolType.CLASSIFICATION,
            {
                "text": text,
                "categories": categories
            }
        )
        return (
            result.get("category", "UNKNOWN"),
            result.get("confidence", 0.0)
        )

    async def detect_language(
        self,
        text: str
    ) -> Tuple[str, float]:
        """Detect the language of a text document

        Args:
            text: Text to analyze for language detection

        Returns:
            Tuple of (language_code, confidence)
        """
        result = await self.execute_tool(
            LLMToolType.LANGUAGE_DETECTION,
            {"text": text}
        )
        return (
            result.get("language", "unknown"),
            result.get("confidence", 0.0)
        )

    async def answer_question(
        self,
        context: str,
        question: str,
        max_length: int = 200
    ) -> str:
        """Answer a question based on provided context

        Args:
            context: Context text containing information
            question: Question to answer
            max_length: Maximum answer length in words

        Returns:
            Answer to the question
        """
        result = await self.execute_tool(
            LLMToolType.QUESTION_ANSWERING,
            {
                "context": context,
                "question": question,
                "max_length": max_length
            }
        )
        return result.get("answer", "")

    async def generate_embeddings(
        self,
        text: str,
        model: str = "text-embedding-ada-002"
    ) -> List[float]:
        """Generate embeddings for text

        Args:
            text: Text to generate embeddings for
            model: Embedding model to use

        Returns:
            List of embedding values
        """
        result = await self.execute_tool(
            LLMToolType.EMBEDDING,
            {
                "text": text,
                "model": model
            }
        )
        return result.get("embeddings", [])

    async def process_document_with_ai(
        self,
        document: DocumentMessage,
        operations: List[str]
    ) -> DocumentMessage:
        """Process a document with multiple AI operations

        Args:
            document: Document to process
            operations: List of operations to perform

        Returns:
            Updated document with AI-generated content
        """
        with self.traced_operation(
            "process_document_with_ai",
            document_id=document.metadata.document_id,
            operations=operations
        ):
            try:
                text = document.content.formatted_content or document.content.raw_text or ""

                if "summary" in operations:
                    summary = await self.generate_summary(text, max_length=200)
                    document.metadata.summary = summary

                if "entities" in operations:
                    entities = await self.extract_entities(text)
                    if document.content.structured_data is None:
                        document.content.structured_data = {}
                    document.content.structured_data["entities"] = entities

                if "classify" in operations:
                    category, confidence = await self.classify_document(text)
                    if document.content.structured_data is None:
                        document.content.structured_data = {}
                    document.content.structured_data["classification"] = {
                        "category": category,
                        "confidence": confidence
                    }

                if "embeddings" in operations:
                    embeddings = await self.generate_embeddings(text[:1000])
                    document.content.embeddings = embeddings

                # Add AI processing to tools list
                document.tools.extend([f"llm_{op}" for op in operations])

                self.logger.info(f"Processed document with AI operations: {operations}")
                return document

            except Exception as e:
                self.logger.error(f"Failed to process document with AI: {str(e)}")
                raise

    def get_available_tools(self) -> List[str]:
        """Get list of available LLM tools

        Returns:
            List of tool names
        """
        return [tool.value for tool in ToolRegistry.get_available_tools()]

    def get_tool_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all available tools

        Returns:
            Dictionary with tool information
        """
        return ToolRegistry.get_tool_info()

    async def health_check(self) -> Dict[str, Any]:
        """Check service health with dynamic capability detection

        Returns:
            Health status dictionary with dynamically generated capabilities
        """
        with self.traced_operation("health_check"):
            try:
                # Check API availability
                api_available = (
                    self.llm_client.openai_client is not None or
                    self.llm_client.anthropic_client is not None
                )

                # Get available tools dynamically
                available_tools = self.get_available_tools()

                # Dynamically generate capabilities from registered tools
                capabilities = self._get_dynamic_capabilities()

                health_status = {
                    "service": "LLMService",
                    "status": "healthy" if api_available else "degraded",
                    "provider": self.provider.value,
                    "architecture": "tool-based",  # Could be from config
                    "available_tools": available_tools,
                    "tool_count": len(available_tools),
                    "capabilities": capabilities,
                    "configuration": {
                        "max_tokens": self.llm_client.max_tokens,
                        "temperature": self.llm_client.temperature,
                        "model": self.llm_client.model
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }

                self.logger.info(f"Health check: {health_status['status']}")
                return health_status

            except Exception as e:
                self.logger.error(f"Health check failed: {str(e)}")
                return {
                    "service": "LLMService",
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }

    def _get_dynamic_capabilities(self) -> List[str]:
        """Generate capabilities list dynamically from registered tools

        Returns:
            Sorted list of unique capabilities derived from tool metadata
        """
        capabilities = set()

        # Map tool capabilities to user-friendly service capabilities
        capability_mapping = {
            ToolCapability.TEXT_GENERATION: ["summarization", "markdown_formatting"],
            ToolCapability.TEXT_ANALYSIS: ["entity_extraction", "language_detection"],
            ToolCapability.TEXT_TRANSFORMATION: ["markdown_formatting"],
            ToolCapability.CLASSIFICATION: ["classification"],
            ToolCapability.QUESTION_ANSWERING: ["question_answering"],
            ToolCapability.EMBEDDING_GENERATION: ["embeddings"],
            ToolCapability.EXTRACTION: ["entity_extraction"]
        }

        # Get capabilities from all registered tools
        for tool_type in ToolRegistry.get_available_tools():
            metadata = ToolRegistry.get_tool_metadata(tool_type)
            if metadata:
                # Add capabilities based on tool metadata
                for capability in metadata.capabilities:
                    # Get mapped capabilities or use capability value as fallback
                    mapped_caps = capability_mapping.get(capability, [capability.value])
                    capabilities.update(mapped_caps)

        return sorted(list(capabilities))


# Register with factory
ServiceFactory.register(ServiceType.LLM, LLMService)