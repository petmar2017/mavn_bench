"""LLM service for AI operations (summarization, entity extraction, Q&A)"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum

from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from .base_service import BaseService
from .service_factory import ServiceFactory, ServiceType
from ..models.document import DocumentMessage, DocumentType
from ..core.config import get_settings


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


class Entity:
    """Extracted entity from text"""

    def __init__(
        self,
        text: str,
        entity_type: str,
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.text = text
        self.entity_type = entity_type
        self.confidence = confidence
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary"""
        return {
            "text": self.text,
            "type": self.entity_type,
            "confidence": self.confidence,
            "metadata": self.metadata
        }


class LLMService(BaseService):
    """Service for LLM operations including summarization, entity extraction, and Q&A"""

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
            self.max_tokens = settings.llm.claude_max_tokens
            self.temperature = settings.llm.claude_temperature
            self.model = settings.llm.claude_model
        elif provider == LLMProvider.OPENAI:
            self.max_tokens = settings.llm.openai_max_tokens
            self.temperature = settings.llm.openai_temperature
            self.model = settings.llm.openai_model
        else:
            # Use default settings (Claude by default)
            self.max_tokens = settings.llm.max_tokens
            self.temperature = settings.llm.temperature
            self.model = settings.llm.default_model

        # Initialize API clients
        self.openai_client = None
        self.anthropic_client = None

        if settings.llm.openai_api_key:
            self.openai_client = AsyncOpenAI(api_key=settings.llm.openai_api_key)

        if settings.llm.anthropic_api_key:
            self.anthropic_client = AsyncAnthropic(api_key=settings.llm.anthropic_api_key)

        self.logger.info(f"Initialized LLMService with provider: {provider}")

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
        with self.traced_operation(
            "generate_summary",
            text_length=len(text),
            max_length=max_length,
            style=style
        ):
            try:
                # Validate input
                if not text or len(text.strip()) == 0:
                    return "No text provided for summarization."

                # Prepare prompt based on style
                prompt = self._prepare_summary_prompt(text, max_length, style)

                # Call LLM API
                summary = await self._call_llm(prompt, max_tokens=max_length * 2)

                self.logger.info(f"Generated {style} summary of {len(text)} chars")
                return summary

            except Exception as e:
                self.logger.error(f"Failed to generate summary: {str(e)}")
                raise

    def _prepare_summary_prompt(self, text: str, max_length: int, style: str) -> str:
        """Prepare prompt for summarization

        Args:
            text: Text to summarize
            max_length: Maximum length
            style: Summary style

        Returns:
            Formatted prompt
        """
        style_instructions = {
            "concise": "Provide a concise summary highlighting key points.",
            "detailed": "Provide a detailed summary covering all major topics.",
            "bullet_points": "Provide a summary in bullet point format."
        }

        instruction = style_instructions.get(style, style_instructions["concise"])

        prompt = f"""Please summarize the following text. {instruction}
Maximum length: approximately {max_length} words.

Text:
{text}

Summary:"""

        return prompt

    async def extract_entities(
        self,
        text: str,
        entity_types: Optional[List[str]] = None
    ) -> List[Entity]:
        """Extract named entities from text

        Args:
            text: Text to extract entities from
            entity_types: Specific entity types to extract (e.g., PERSON, ORGANIZATION, LOCATION)

        Returns:
            List of extracted entities
        """
        with self.traced_operation(
            "extract_entities",
            text_length=len(text),
            entity_types=entity_types
        ):
            try:
                if not text:
                    return []

                # Default entity types if not specified
                if entity_types is None:
                    entity_types = [
                        "PERSON", "ORGANIZATION", "LOCATION", "DATE",
                        "MONEY", "PRODUCT", "EVENT", "EMAIL", "PHONE"
                    ]

                # Prepare extraction prompt
                prompt = self._prepare_entity_prompt(text, entity_types)

                # Call LLM API
                response = await self._call_llm(prompt, temperature=0.3)

                # Parse entities from response
                entities = self._parse_entities(response)

                self.logger.info(f"Extracted {len(entities)} entities from text")
                return entities

            except Exception as e:
                self.logger.error(f"Failed to extract entities: {str(e)}")
                raise

    def _prepare_entity_prompt(self, text: str, entity_types: List[str]) -> str:
        """Prepare prompt for entity extraction

        Args:
            text: Text to analyze
            entity_types: Entity types to extract

        Returns:
            Formatted prompt
        """
        types_str = ", ".join(entity_types)

        prompt = f"""Extract the following types of entities from the text: {types_str}

Return the result as a JSON array with objects containing:
- "text": the entity text
- "type": the entity type
- "confidence": confidence score (0-1)

Text:
{text}

Entities (JSON format):"""

        return prompt

    def _parse_entities(self, response: str) -> List[Entity]:
        """Parse entities from LLM response

        Args:
            response: LLM response containing entities

        Returns:
            List of Entity objects
        """
        entities = []

        # Try to parse as JSON
        if response.strip().startswith('['):
            try:
                entity_data = json.loads(response)
                for item in entity_data:
                    entity = Entity(
                        text=item.get("text", ""),
                        entity_type=item.get("type", "UNKNOWN"),
                        confidence=item.get("confidence", 1.0)
                    )
                    entities.append(entity)
                return entities  # Return early if JSON parsing succeeded
            except json.JSONDecodeError:
                pass  # Fall through to text parsing

        # Fallback: parse as text lines
        lines = response.strip().split('\n')
        for line in lines:
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    entity_type = parts[0].strip().upper()
                    if entity_type == "ORGANIZATION":
                        entity_type = "ORG"
                    entity_text = parts[1].strip()
                    entities.append(Entity(
                        text=entity_text,
                        entity_type=entity_type,
                        confidence=1.0
                    ))

        return entities

    async def classify_document(
        self,
        text: str,
        categories: Optional[List[str]] = None
    ) -> Tuple[str, float]:
        """Classify document into categories

        Args:
            text: Document text to classify
            categories: Possible categories (uses default if not provided)

        Returns:
            Tuple of (category, confidence)
        """
        with self.traced_operation(
            "classify_document",
            text_length=len(text),
            categories=categories
        ):
            try:
                if not text:
                    return ("UNKNOWN", 0.0)

                # Default categories if not provided
                if categories is None:
                    categories = [
                        "Technical Documentation",
                        "Business Report",
                        "Legal Document",
                        "Financial Statement",
                        "Research Paper",
                        "News Article",
                        "Personal Communication",
                        "Marketing Material"
                    ]

                # Prepare classification prompt
                prompt = self._prepare_classification_prompt(text, categories)

                # Call LLM API
                response = await self._call_llm(prompt, temperature=0.3)

                # Parse classification result
                category, confidence = self._parse_classification(response, categories)

                self.logger.info(f"Classified document as {category} with confidence {confidence}")
                return (category, confidence)

            except Exception as e:
                self.logger.error(f"Failed to classify document: {str(e)}")
                raise

    def _prepare_classification_prompt(self, text: str, categories: List[str]) -> str:
        """Prepare prompt for document classification

        Args:
            text: Text to classify
            categories: Available categories

        Returns:
            Formatted prompt
        """
        categories_str = "\n".join(f"- {cat}" for cat in categories)

        prompt = f"""Classify the following text into one of these categories:
{categories_str}

Return your answer in the format:
Category: [chosen category]
Confidence: [0.0-1.0]

Text:
{text[:2000]}  # Limit text length for classification

Classification:"""

        return prompt

    def _parse_classification(
        self,
        response: str,
        categories: List[str]
    ) -> Tuple[str, float]:
        """Parse classification result from LLM response

        Args:
            response: LLM response
            categories: Valid categories

        Returns:
            Tuple of (category, confidence)
        """
        category = "UNKNOWN"
        confidence = 0.0

        lines = response.strip().split('\n')
        for line in lines:
            if "Category:" in line or "category:" in line:
                cat_text = line.split(':')[1].strip()
                # Find best matching category
                for cat in categories:
                    if cat.lower() in cat_text.lower() or cat_text.lower() in cat.lower():
                        category = cat
                        break
            elif "Confidence:" in line or "confidence:" in line:
                try:
                    conf_text = line.split(':')[1].strip()
                    confidence = float(conf_text.replace('%', '').strip()) / 100 if '%' in conf_text else float(conf_text)
                    confidence = min(1.0, max(0.0, confidence))
                except ValueError:
                    confidence = 0.8  # Default confidence

        return (category, confidence)

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
        with self.traced_operation(
            "answer_question",
            context_length=len(context),
            question=question[:100]
        ):
            try:
                if not context or not question:
                    return "Insufficient information provided."

                # Prepare Q&A prompt
                prompt = self._prepare_qa_prompt(context, question, max_length)

                # Call LLM API
                answer = await self._call_llm(prompt, max_tokens=max_length * 2)

                self.logger.info(f"Answered question: {question[:50]}...")
                return answer

            except Exception as e:
                self.logger.error(f"Failed to answer question: {str(e)}")
                raise

    def _prepare_qa_prompt(self, context: str, question: str, max_length: int) -> str:
        """Prepare prompt for question answering

        Args:
            context: Context text
            question: Question to answer
            max_length: Maximum answer length

        Returns:
            Formatted prompt
        """
        prompt = f"""Based on the following context, please answer the question.
If the answer cannot be found in the context, say "Information not found in the provided context."
Maximum answer length: {max_length} words.

Context:
{context}

Question: {question}

Answer:"""

        return prompt

    async def _call_llm(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """Call the LLM API (placeholder for actual implementation)

        Args:
            prompt: Prompt to send to LLM
            max_tokens: Maximum tokens in response
            temperature: Temperature for generation

        Returns:
            LLM response
        """
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature

        try:
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
                # Fallback for testing without API keys
                self.logger.warning(f"No API client configured for {self.provider}, using mock response")
                await asyncio.sleep(0.1)  # Simulate API latency

                if "summary" in prompt.lower():
                    return "This is a generated summary of the provided text highlighting the key points and main ideas."
                elif "entities" in prompt.lower():
                    return '[{"text": "Example Entity", "type": "ORG", "confidence": 0.9}]'
                elif "classify" in prompt.lower():
                    return "Category: Technical Documentation\nConfidence: 0.85"
                elif "question" in prompt.lower():
                    return "Based on the provided context, the answer to your question is..."
                else:
                    return "Generated response from LLM."

        except Exception as e:
            self.logger.error(f"LLM API call failed: {str(e)}")
            raise

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
        with self.traced_operation(
            "generate_embeddings",
            text_length=len(text),
            model=model
        ):
            try:
                if self.openai_client:
                    # Use OpenAI for embeddings (Anthropic doesn't have embeddings API)
                    response = await self.openai_client.embeddings.create(
                        model=model,
                        input=text
                    )
                    embeddings = response.data[0].embedding
                    self.logger.info(f"Generated embeddings of dimension {len(embeddings)}")
                    return embeddings
                else:
                    # Fallback for testing without API keys
                    self.logger.warning("No OpenAI client configured, using mock embeddings")
                    await asyncio.sleep(0.1)

                    # Return mock embeddings (normally would be 1536 dimensions for ada-002)
                    import random
                    embeddings = [random.random() for _ in range(384)]  # Smaller for demo

                    self.logger.info(f"Generated mock embeddings of dimension {len(embeddings)}")
                    return embeddings

            except Exception as e:
                self.logger.error(f"Failed to generate embeddings: {str(e)}")
                raise

    async def process_document_with_ai(
        self,
        document: DocumentMessage,
        operations: List[str]
    ) -> DocumentMessage:
        """Process a document with multiple AI operations

        Args:
            document: Document to process
            operations: List of operations to perform (summary, entities, classify, embeddings)

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
                    document.content.structured_data["entities"] = [e.to_dict() for e in entities]

                if "classify" in operations:
                    category, confidence = await self.classify_document(text)
                    if document.content.structured_data is None:
                        document.content.structured_data = {}
                    document.content.structured_data["classification"] = {
                        "category": category,
                        "confidence": confidence
                    }

                if "embeddings" in operations:
                    embeddings = await self.generate_embeddings(text[:1000])  # Limit text for embeddings
                    document.content.embeddings = embeddings

                # Add AI processing to tools list
                document.tools.extend([f"llm_{op}" for op in operations])

                self.logger.info(f"Processed document with AI operations: {operations}")
                return document

            except Exception as e:
                self.logger.error(f"Failed to process document with AI: {str(e)}")
                raise

    async def health_check(self) -> Dict[str, Any]:
        """Check service health

        Returns:
            Health status dictionary
        """
        with self.traced_operation("health_check"):
            try:
                # Check API availability (mock for now)
                api_available = True  # Would check actual API connection

                health_status = {
                    "service": "LLMService",
                    "status": "healthy" if api_available else "degraded",
                    "provider": self.provider.value,
                    "capabilities": [
                        "summarization",
                        "entity_extraction",
                        "classification",
                        "question_answering",
                        "embeddings"
                    ],
                    "configuration": {
                        "max_tokens": self.max_tokens,
                        "temperature": self.temperature
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


# Register with factory
ServiceFactory.register(ServiceType.LLM, LLMService)