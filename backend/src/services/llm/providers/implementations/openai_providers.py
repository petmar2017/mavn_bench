"""OpenAI model provider implementations"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio

from openai import AsyncOpenAI

from ..base_provider import (
    BaseModelProvider,
    ModelMetadata,
    ModelCapabilities,
    CostProfile,
    CostTier
)
from ..provider_decorators import register_provider
from .....core.config import get_settings


@register_provider("openai-gpt-4o")
class GPT4OptimizedProvider(BaseModelProvider):
    """GPT-4 Optimized - High quality with function calling"""

    def get_metadata(self) -> ModelMetadata:
        """Get provider metadata from config"""
        settings = get_settings()
        config = settings.llm.providers.get("openai-gpt-4o", {})

        return ModelMetadata(
            name=config.get("name", "GPT-4 Optimized"),
            provider="openai",
            model_id=config.get("model_id", "gpt-4o"),
            version="4.0",
            capabilities=(
                ModelCapabilities.TEXT_GENERATION |
                ModelCapabilities.FUNCTION_CALLING |
                ModelCapabilities.VISION |
                ModelCapabilities.JSON_MODE
            ),
            cost_profile=CostProfile(
                tier=CostTier(config.get("cost_tier", "premium")),
                cost_per_1k_input=config.get("cost_per_1k_input", 0.005),
                cost_per_1k_output=config.get("cost_per_1k_output", 0.015),
                avg_latency_ms=config.get("avg_latency_ms", 1500),
                max_context=config.get("max_context", 128000)
            ),
            quality_score=config.get("quality_score", 0.93),
            description="OpenAI's optimized GPT-4 with multimodal capabilities",
            created_at=datetime.now()
        )

    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize OpenAI client"""
        settings = get_settings()
        api_key = config.get("api_key") or settings.llm.openai_api_key

        if api_key:
            self._client = AsyncOpenAI(api_key=api_key)

    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Generate text using GPT-4"""
        if not self._client:
            # Fallback for testing
            await asyncio.sleep(0.1)
            return f"[GPT-4o Mock] Response to: {prompt[:50]}..."

        settings = get_settings()
        config = settings.llm.providers.get("openai-gpt-4o", {})

        response = await self._client.chat.completions.create(
            model=self._metadata.model_id,
            max_tokens=max_tokens or config.get("max_tokens", 4000),
            temperature=temperature or config.get("temperature", 0.3),
            messages=[{"role": "user", "content": prompt}],
            stop=stop,
            **kwargs
        )

        return response.choices[0].message.content

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
            yield "[GPT-4o Mock] "
            for word in prompt.split()[:10]:
                await asyncio.sleep(0.05)
                yield word + " "
            return

        settings = get_settings()
        config = settings.llm.providers.get("openai-gpt-4o", {})

        stream = await self._client.chat.completions.create(
            model=self._metadata.model_id,
            max_tokens=max_tokens or config.get("max_tokens", 4000),
            temperature=temperature or config.get("temperature", 0.3),
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            **kwargs
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def generate_embeddings(
        self,
        text: str,
        model: Optional[str] = None,
        **kwargs
    ) -> List[float]:
        """Generate embeddings using OpenAI"""
        if not self._client:
            # Mock embeddings
            import random
            return [random.random() for _ in range(1536)]

        response = await self._client.embeddings.create(
            model=model or "text-embedding-3-small",
            input=text,
            **kwargs
        )

        return response.data[0].embedding

    async def health_check(self) -> Dict[str, Any]:
        """Check provider health"""
        return {
            "provider": "openai-gpt-4o",
            "status": "healthy" if self._client else "no_api_key",
            "model": self._metadata.model_id,
            "capabilities": [
                "text_generation",
                "function_calling",
                "vision",
                "json_mode"
            ]
        }


@register_provider("openai-gpt-4o-mini")
class GPT4MiniProvider(BaseModelProvider):
    """GPT-4 Mini - Fast and economical"""

    def get_metadata(self) -> ModelMetadata:
        """Get provider metadata from config"""
        settings = get_settings()
        config = settings.llm.providers.get("openai-gpt-4o-mini", {})

        return ModelMetadata(
            name=config.get("name", "GPT-4 Mini"),
            provider="openai",
            model_id=config.get("model_id", "gpt-4o-mini"),
            version="4.0-mini",
            capabilities=(
                ModelCapabilities.TEXT_GENERATION |
                ModelCapabilities.FAST_INFERENCE |
                ModelCapabilities.FUNCTION_CALLING
            ),
            cost_profile=CostProfile(
                tier=CostTier(config.get("cost_tier", "economy")),
                cost_per_1k_input=config.get("cost_per_1k_input", 0.00015),
                cost_per_1k_output=config.get("cost_per_1k_output", 0.0006),
                avg_latency_ms=config.get("avg_latency_ms", 800),
                max_context=config.get("max_context", 128000)
            ),
            quality_score=config.get("quality_score", 0.80),
            description="Cost-effective GPT-4 variant for simple tasks",
            created_at=datetime.now()
        )

    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize OpenAI client"""
        settings = get_settings()
        api_key = config.get("api_key") or settings.llm.openai_api_key

        if api_key:
            self._client = AsyncOpenAI(api_key=api_key)

    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Generate text using GPT-4 Mini"""
        if not self._client:
            # Fallback for testing
            await asyncio.sleep(0.05)
            return f"[GPT-4 Mini Mock] Quick: {prompt[:30]}..."

        settings = get_settings()
        config = settings.llm.providers.get("openai-gpt-4o-mini", {})

        response = await self._client.chat.completions.create(
            model=self._metadata.model_id,
            max_tokens=max_tokens or config.get("max_tokens", 2000),
            temperature=temperature or config.get("temperature", 0.3),
            messages=[{"role": "user", "content": prompt}],
            stop=stop,
            **kwargs
        )

        return response.choices[0].message.content

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
            yield "[Mini Mock] "
            for word in prompt.split()[:5]:
                await asyncio.sleep(0.02)
                yield word + " "
            return

        settings = get_settings()
        config = settings.llm.providers.get("openai-gpt-4o-mini", {})

        stream = await self._client.chat.completions.create(
            model=self._metadata.model_id,
            max_tokens=max_tokens or config.get("max_tokens", 2000),
            temperature=temperature or config.get("temperature", 0.3),
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            **kwargs
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def generate_embeddings(
        self,
        text: str,
        model: Optional[str] = None,
        **kwargs
    ) -> List[float]:
        """Generate embeddings using OpenAI"""
        if not self._client:
            # Mock embeddings
            import random
            return [random.random() for _ in range(1536)]

        response = await self._client.embeddings.create(
            model=model or "text-embedding-3-small",
            input=text,
            **kwargs
        )

        return response.data[0].embedding

    async def health_check(self) -> Dict[str, Any]:
        """Check provider health"""
        return {
            "provider": "openai-gpt-4o-mini",
            "status": "healthy" if self._client else "no_api_key",
            "model": self._metadata.model_id,
            "capabilities": [
                "text_generation",
                "fast_inference",
                "function_calling"
            ]
        }


@register_provider("openai-text-embedding-3-small")
class TextEmbeddingSmallProvider(BaseModelProvider):
    """OpenAI Text Embedding 3 Small - Economical embeddings"""

    def get_metadata(self) -> ModelMetadata:
        """Get provider metadata from config"""
        settings = get_settings()
        config = settings.llm.providers.get("openai-text-embedding-3-small", {})

        return ModelMetadata(
            name=config.get("name", "Text Embedding 3 Small"),
            provider="openai",
            model_id=config.get("model_id", "text-embedding-3-small"),
            version="3",
            capabilities=ModelCapabilities.EMBEDDINGS,
            cost_profile=CostProfile(
                tier=CostTier(config.get("cost_tier", "economy")),
                cost_per_1k_input=config.get("cost_per_1k_input", 0.00002),
                cost_per_1k_output=0.0,
                avg_latency_ms=config.get("avg_latency_ms", 100),
                max_context=config.get("max_context", 8191)
            ),
            quality_score=config.get("quality_score", 0.85),
            description="Cost-effective embedding model",
            created_at=datetime.now()
        )

    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize OpenAI client"""
        settings = get_settings()
        api_key = config.get("api_key") or settings.llm.openai_api_key

        if api_key:
            self._client = AsyncOpenAI(api_key=api_key)

    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Embedding models don't generate text"""
        raise NotImplementedError("Embedding models don't support text generation")

    async def generate_streaming(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ):
        """Embedding models don't support streaming"""
        raise NotImplementedError("Embedding models don't support streaming")

    async def generate_embeddings(
        self,
        text: str,
        model: Optional[str] = None,
        **kwargs
    ) -> List[float]:
        """Generate embeddings"""
        if not self._client:
            # Mock embeddings
            import random
            return [random.random() for _ in range(1536)]

        response = await self._client.embeddings.create(
            model=self._metadata.model_id,
            input=text,
            **kwargs
        )

        return response.data[0].embedding

    async def health_check(self) -> Dict[str, Any]:
        """Check provider health"""
        return {
            "provider": "openai-text-embedding-3-small",
            "status": "healthy" if self._client else "no_api_key",
            "model": self._metadata.model_id,
            "capabilities": ["embeddings"]
        }


@register_provider("openai-text-embedding-3-large")
class TextEmbeddingLargeProvider(BaseModelProvider):
    """OpenAI Text Embedding 3 Large - High quality embeddings"""

    def get_metadata(self) -> ModelMetadata:
        """Get provider metadata from config"""
        settings = get_settings()
        config = settings.llm.providers.get("openai-text-embedding-3-large", {})

        return ModelMetadata(
            name=config.get("name", "Text Embedding 3 Large"),
            provider="openai",
            model_id=config.get("model_id", "text-embedding-3-large"),
            version="3",
            capabilities=ModelCapabilities.EMBEDDINGS,
            cost_profile=CostProfile(
                tier=CostTier(config.get("cost_tier", "standard")),
                cost_per_1k_input=config.get("cost_per_1k_input", 0.00013),
                cost_per_1k_output=0.0,
                avg_latency_ms=config.get("avg_latency_ms", 150),
                max_context=config.get("max_context", 8191)
            ),
            quality_score=config.get("quality_score", 0.95),
            description="High-quality embedding model for RAG",
            created_at=datetime.now()
        )

    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize OpenAI client"""
        settings = get_settings()
        api_key = config.get("api_key") or settings.llm.openai_api_key

        if api_key:
            self._client = AsyncOpenAI(api_key=api_key)

    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Embedding models don't generate text"""
        raise NotImplementedError("Embedding models don't support text generation")

    async def generate_streaming(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ):
        """Embedding models don't support streaming"""
        raise NotImplementedError("Embedding models don't support streaming")

    async def generate_embeddings(
        self,
        text: str,
        model: Optional[str] = None,
        **kwargs
    ) -> List[float]:
        """Generate embeddings"""
        if not self._client:
            # Mock embeddings
            import random
            return [random.random() for _ in range(3072)]  # Large model has more dimensions

        response = await self._client.embeddings.create(
            model=self._metadata.model_id,
            input=text,
            **kwargs
        )

        return response.data[0].embedding

    async def health_check(self) -> Dict[str, Any]:
        """Check provider health"""
        return {
            "provider": "openai-text-embedding-3-large",
            "status": "healthy" if self._client else "no_api_key",
            "model": self._metadata.model_id,
            "capabilities": ["embeddings"]
        }