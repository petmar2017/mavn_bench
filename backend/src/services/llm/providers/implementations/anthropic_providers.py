"""Anthropic model provider implementations"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio

from anthropic import AsyncAnthropic

from ..base_provider import (
    BaseModelProvider,
    ModelMetadata,
    ModelCapabilities,
    CostProfile,
    CostTier
)
from ..provider_decorators import register_provider
from .....core.config import get_settings


@register_provider("anthropic-claude-3.5-sonnet")
class ClaudeSonnetProvider(BaseModelProvider):
    """Claude 3.5 Sonnet - High quality detailed reasoning"""

    def get_metadata(self) -> ModelMetadata:
        """Get provider metadata from config"""
        settings = get_settings()
        config = settings.llm.providers.get("anthropic-claude-3.5-sonnet", {})

        return ModelMetadata(
            name=config.get("name", "Claude 3.5 Sonnet"),
            provider="anthropic",
            model_id=config.get("model_id", "claude-3-5-sonnet-20241022"),
            version="3.5",
            capabilities=(
                ModelCapabilities.TEXT_GENERATION |
                ModelCapabilities.LONG_CONTEXT |
                ModelCapabilities.JSON_MODE
            ),
            cost_profile=CostProfile(
                tier=CostTier(config.get("cost_tier", "premium")),
                cost_per_1k_input=config.get("cost_per_1k_input", 0.003),
                cost_per_1k_output=config.get("cost_per_1k_output", 0.015),
                avg_latency_ms=config.get("avg_latency_ms", 2000),
                max_context=config.get("max_context", 200000)
            ),
            quality_score=config.get("quality_score", 0.95),
            description="Anthropic's most capable model for complex reasoning",
            created_at=datetime.now()
        )

    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize Anthropic client"""
        settings = get_settings()
        api_key = config.get("api_key") or settings.llm.anthropic_api_key

        if api_key:
            self._client = AsyncAnthropic(api_key=api_key)

    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Generate text using Claude"""
        if not self._client:
            # Fallback for testing
            await asyncio.sleep(0.1)
            return f"[Claude Sonnet Mock] Response to: {prompt[:50]}..."

        settings = get_settings()
        config = settings.llm.providers.get("anthropic-claude-3.5-sonnet", {})

        response = await self._client.messages.create(
            model=self._metadata.model_id,
            max_tokens=max_tokens or config.get("max_tokens", 4000),
            temperature=temperature or config.get("temperature", 0.3),
            messages=[{"role": "user", "content": prompt}],
            stop_sequences=stop,
            **kwargs
        )

        return response.content[0].text

    async def generate_streaming(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ):
        """Generate with streaming"""
        if not self._client:
            # Mock streaming
            yield "[Claude Sonnet Mock] "
            for word in prompt.split()[:10]:
                await asyncio.sleep(0.05)
                yield word + " "
            return

        settings = get_settings()
        config = settings.llm.providers.get("anthropic-claude-3.5-sonnet", {})

        async with self._client.messages.stream(
            model=self._metadata.model_id,
            max_tokens=max_tokens or config.get("max_tokens", 4000),
            temperature=temperature or config.get("temperature", 0.3),
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def generate_embeddings(
        self,
        text: str,
        model: Optional[str] = None,
        **kwargs
    ) -> List[float]:
        """Claude doesn't support embeddings directly"""
        raise NotImplementedError("Claude models don't support embedding generation")

    async def health_check(self) -> Dict[str, Any]:
        """Check provider health"""
        return {
            "provider": "anthropic-claude-3.5-sonnet",
            "status": "healthy" if self._client else "no_api_key",
            "model": self._metadata.model_id,
            "capabilities": [
                "text_generation",
                "long_context",
                "json_mode"
            ]
        }


@register_provider("anthropic-claude-3.5-haiku")
class ClaudeHaikuProvider(BaseModelProvider):
    """Claude 3.5 Haiku - Fast and economical"""

    def get_metadata(self) -> ModelMetadata:
        """Get provider metadata from config"""
        settings = get_settings()
        config = settings.llm.providers.get("anthropic-claude-3.5-haiku", {})

        return ModelMetadata(
            name=config.get("name", "Claude 3.5 Haiku"),
            provider="anthropic",
            model_id=config.get("model_id", "claude-3-5-haiku-20241022"),
            version="3.5",
            capabilities=(
                ModelCapabilities.TEXT_GENERATION |
                ModelCapabilities.FAST_INFERENCE |
                ModelCapabilities.LONG_CONTEXT
            ),
            cost_profile=CostProfile(
                tier=CostTier(config.get("cost_tier", "economy")),
                cost_per_1k_input=config.get("cost_per_1k_input", 0.0008),
                cost_per_1k_output=config.get("cost_per_1k_output", 0.004),
                avg_latency_ms=config.get("avg_latency_ms", 500),
                max_context=config.get("max_context", 200000)
            ),
            quality_score=config.get("quality_score", 0.85),
            description="Fast and cost-effective Claude model",
            created_at=datetime.now()
        )

    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize Anthropic client"""
        settings = get_settings()
        api_key = config.get("api_key") or settings.llm.anthropic_api_key

        if api_key:
            self._client = AsyncAnthropic(api_key=api_key)

    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Generate text using Claude Haiku"""
        if not self._client:
            # Fallback for testing
            await asyncio.sleep(0.05)
            return f"[Claude Haiku Mock] Quick response: {prompt[:30]}..."

        settings = get_settings()
        config = settings.llm.providers.get("anthropic-claude-3.5-haiku", {})

        response = await self._client.messages.create(
            model=self._metadata.model_id,
            max_tokens=max_tokens or config.get("max_tokens", 1000),
            temperature=temperature or config.get("temperature", 0.3),
            messages=[{"role": "user", "content": prompt}],
            stop_sequences=stop,
            **kwargs
        )

        return response.content[0].text

    async def generate_streaming(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ):
        """Generate with streaming"""
        if not self._client:
            # Mock streaming
            yield "[Haiku Mock] "
            for word in prompt.split()[:5]:
                await asyncio.sleep(0.02)
                yield word + " "
            return

        settings = get_settings()
        config = settings.llm.providers.get("anthropic-claude-3.5-haiku", {})

        async with self._client.messages.stream(
            model=self._metadata.model_id,
            max_tokens=max_tokens or config.get("max_tokens", 1000),
            temperature=temperature or config.get("temperature", 0.3),
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def generate_embeddings(
        self,
        text: str,
        model: Optional[str] = None,
        **kwargs
    ) -> List[float]:
        """Claude doesn't support embeddings directly"""
        raise NotImplementedError("Claude models don't support embedding generation")

    async def health_check(self) -> Dict[str, Any]:
        """Check provider health"""
        return {
            "provider": "anthropic-claude-3.5-haiku",
            "status": "healthy" if self._client else "no_api_key",
            "model": self._metadata.model_id,
            "capabilities": [
                "text_generation",
                "fast_inference",
                "long_context"
            ]
        }