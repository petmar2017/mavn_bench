"""Base provider architecture for multi-model LLM support"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Flag, auto, Enum
from dataclasses import dataclass
from datetime import datetime


class ModelCapabilities(Flag):
    """Capabilities that a model provider supports"""
    TEXT_GENERATION = auto()
    EMBEDDINGS = auto()
    VISION = auto()
    FUNCTION_CALLING = auto()
    LONG_CONTEXT = auto()  # >100k tokens
    FAST_INFERENCE = auto()  # <500ms latency
    JSON_MODE = auto()  # Structured output
    STREAMING = auto()  # Stream responses
    BATCH = auto()  # Batch processing


class CostTier(str, Enum):
    """Cost tiers for model usage"""
    PREMIUM = "premium"  # Most expensive, highest quality
    STANDARD = "standard"  # Balanced cost/quality
    ECONOMY = "economy"  # Cheapest, basic quality


@dataclass
class CostProfile:
    """Cost and performance characteristics of a model"""
    tier: CostTier
    cost_per_1k_input: float  # USD per 1k input tokens
    cost_per_1k_output: float  # USD per 1k output tokens
    avg_latency_ms: int  # Average latency in milliseconds
    max_context: int  # Maximum context window in tokens
    tokens_per_second: Optional[int] = None  # Generation speed


@dataclass
class TaskRequirements:
    """Requirements for a specific task"""
    max_latency_ms: Optional[int] = None
    max_cost_tier: CostTier = CostTier.STANDARD
    min_quality_score: float = 0.7  # 0.0 to 1.0
    required_context: int = 0
    needs_vision: bool = False
    needs_streaming: bool = False
    needs_json_mode: bool = False
    preferred_provider: Optional[str] = None  # User preference


@dataclass
class ModelMetadata:
    """Metadata about a model provider"""
    name: str
    provider: str  # anthropic, openai, google, etc.
    model_id: str  # Actual model identifier
    version: str
    capabilities: ModelCapabilities
    cost_profile: CostProfile
    quality_score: float  # 0.0 to 1.0 quality rating
    description: str
    created_at: datetime
    deprecated: bool = False
    replacement_model: Optional[str] = None  # If deprecated


class BaseModelProvider(ABC):
    """Abstract base class for all model providers

    This class defines the interface that all model providers must implement.
    Each provider encapsulates the specifics of interacting with a particular
    LLM model or API service.
    """

    def __init__(self):
        """Initialize the provider"""
        self._metadata = self.get_metadata()
        self._client = None

    @abstractmethod
    def get_metadata(self) -> ModelMetadata:
        """Get metadata about this model provider

        Returns:
            ModelMetadata describing the provider's capabilities
        """
        pass

    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the provider with configuration

        Args:
            config: Provider-specific configuration
        """
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Generate text completion

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 1.0)
            stop: Stop sequences
            **kwargs: Provider-specific parameters

        Returns:
            Generated text
        """
        pass

    @abstractmethod
    async def generate_streaming(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ):
        """Generate text completion with streaming

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Provider-specific parameters

        Yields:
            Chunks of generated text
        """
        pass

    @abstractmethod
    async def generate_embeddings(
        self,
        text: str,
        model: Optional[str] = None,
        **kwargs
    ) -> List[float]:
        """Generate embeddings for text

        Args:
            text: Input text
            model: Embedding model to use
            **kwargs: Provider-specific parameters

        Returns:
            List of embedding values
        """
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check provider health and availability

        Returns:
            Health status dictionary
        """
        pass

    def supports_capability(self, capability: ModelCapabilities) -> bool:
        """Check if provider supports a capability

        Args:
            capability: Capability to check

        Returns:
            True if capability is supported
        """
        return bool(self._metadata.capabilities & capability)

    def get_cost_estimate(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for a request

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        profile = self._metadata.cost_profile
        input_cost = (input_tokens / 1000) * profile.cost_per_1k_input
        output_cost = (output_tokens / 1000) * profile.cost_per_1k_output
        return input_cost + output_cost

    def meets_requirements(self, requirements: TaskRequirements) -> bool:
        """Check if provider meets task requirements

        Args:
            requirements: Task requirements to check

        Returns:
            True if all requirements are met
        """
        metadata = self._metadata
        profile = metadata.cost_profile

        # Check latency
        if requirements.max_latency_ms and profile.avg_latency_ms > requirements.max_latency_ms:
            return False

        # Check cost tier
        tier_order = {CostTier.ECONOMY: 0, CostTier.STANDARD: 1, CostTier.PREMIUM: 2}
        if tier_order[profile.tier] > tier_order[requirements.max_cost_tier]:
            return False

        # Check quality
        if metadata.quality_score < requirements.min_quality_score:
            return False

        # Check context
        if requirements.required_context > profile.max_context:
            return False

        # Check capabilities
        if requirements.needs_vision and not self.supports_capability(ModelCapabilities.VISION):
            return False

        if requirements.needs_streaming and not self.supports_capability(ModelCapabilities.STREAMING):
            return False

        if requirements.needs_json_mode and not self.supports_capability(ModelCapabilities.JSON_MODE):
            return False

        return True

    async def shutdown(self) -> None:
        """Cleanup provider resources"""
        if self._client:
            # Provider-specific cleanup
            pass