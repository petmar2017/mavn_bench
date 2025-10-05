"""Unit tests for LLM provider architecture"""

import pytest
import asyncio
from typing import Dict, Any, List
from datetime import datetime

from src.services.llm.providers.base_provider import (
    BaseModelProvider,
    ModelMetadata,
    ModelCapabilities,
    CostProfile,
    CostTier,
    TaskRequirements
)
from src.services.llm.providers.provider_registry import ModelProviderRegistry
from src.services.llm.providers.model_selector import ModelSelector, SelectionStrategy
from src.services.llm.tool_registry import LLMToolType


class TestModelProviderBase:
    """Test base provider functionality"""

    def test_model_capabilities_flags(self):
        """Test capability flags work correctly"""
        caps = ModelCapabilities.TEXT_GENERATION | ModelCapabilities.VISION

        assert caps & ModelCapabilities.TEXT_GENERATION
        assert caps & ModelCapabilities.VISION
        assert not (caps & ModelCapabilities.EMBEDDINGS)

    def test_cost_profile_creation(self):
        """Test cost profile data structure"""
        profile = CostProfile(
            tier=CostTier.PREMIUM,
            cost_per_1k_input=0.003,
            cost_per_1k_output=0.015,
            avg_latency_ms=2000,
            max_context=200000
        )

        assert profile.tier == CostTier.PREMIUM
        assert profile.cost_per_1k_input == 0.003
        assert profile.max_context == 200000

    def test_task_requirements(self):
        """Test task requirements structure"""
        req = TaskRequirements(
            max_latency_ms=1000,
            max_cost_tier=CostTier.STANDARD,
            min_quality_score=0.8,
            required_context=10000,
            needs_vision=True
        )

        assert req.max_latency_ms == 1000
        assert req.max_cost_tier == CostTier.STANDARD
        assert req.needs_vision is True


class TestProviderRegistry:
    """Test provider registry functionality"""

    @pytest.fixture(autouse=True)
    def clear_registry(self):
        """Clear registry before each test"""
        ModelProviderRegistry.clear()
        yield
        ModelProviderRegistry.clear()

    def test_register_provider(self):
        """Test provider registration"""
        # Create mock provider
        class MockProvider(BaseModelProvider):
            def get_metadata(self) -> ModelMetadata:
                return ModelMetadata(
                    name="Mock Provider",
                    provider="mock",
                    model_id="mock-1",
                    version="1.0",
                    capabilities=ModelCapabilities.TEXT_GENERATION,
                    cost_profile=CostProfile(
                        tier=CostTier.STANDARD,
                        cost_per_1k_input=0.001,
                        cost_per_1k_output=0.002,
                        avg_latency_ms=1000,
                        max_context=4096
                    ),
                    quality_score=0.85,
                    description="Test provider",
                    created_at=datetime.now()
                )

            async def initialize(self, config: Dict[str, Any]) -> None:
                pass

            async def generate(self, prompt: str, **kwargs) -> str:
                return f"Mock response: {prompt}"

            async def generate_streaming(self, prompt: str, **kwargs):
                yield "Mock streaming"

            async def generate_embeddings(self, text: str, **kwargs) -> List[float]:
                return [0.0] * 768

            async def health_check(self) -> Dict[str, Any]:
                return {"status": "healthy"}

        # Register provider
        ModelProviderRegistry.register("mock-provider", MockProvider)

        # Check it was registered
        providers = ModelProviderRegistry.get_available_providers()
        assert "mock-provider" in providers

    @pytest.mark.asyncio
    async def test_create_provider_instance(self):
        """Test creating provider instance"""
        # Create and register mock provider
        class MockProvider(BaseModelProvider):
            def get_metadata(self) -> ModelMetadata:
                return ModelMetadata(
                    name="Mock",
                    provider="mock",
                    model_id="mock-1",
                    version="1.0",
                    capabilities=ModelCapabilities.TEXT_GENERATION,
                    cost_profile=CostProfile(
                        tier=CostTier.STANDARD,
                        cost_per_1k_input=0.001,
                        cost_per_1k_output=0.002,
                        avg_latency_ms=1000,
                        max_context=4096
                    ),
                    quality_score=0.85,
                    description="Test",
                    created_at=datetime.now()
                )

            async def initialize(self, config: Dict[str, Any]) -> None:
                self.initialized = True

            async def generate(self, prompt: str, **kwargs) -> str:
                return "response"

            async def generate_streaming(self, prompt: str, **kwargs):
                yield "stream"

            async def generate_embeddings(self, text: str, **kwargs) -> List[float]:
                return [0.0]

            async def health_check(self) -> Dict[str, Any]:
                return {"status": "ok"}

        ModelProviderRegistry.register("mock", MockProvider)

        # Create instance
        provider = await ModelProviderRegistry.create("mock", {"test": True})

        assert provider is not None
        assert isinstance(provider, MockProvider)
        assert hasattr(provider, 'initialized')

    def test_get_provider_metadata(self):
        """Test getting provider metadata"""
        # Create mock provider with specific metadata
        class MockProvider(BaseModelProvider):
            def get_metadata(self) -> ModelMetadata:
                return ModelMetadata(
                    name="Test Provider",
                    provider="test",
                    model_id="test-model",
                    version="2.0",
                    capabilities=ModelCapabilities.TEXT_GENERATION | ModelCapabilities.VISION,
                    cost_profile=CostProfile(
                        tier=CostTier.PREMIUM,
                        cost_per_1k_input=0.005,
                        cost_per_1k_output=0.015,
                        avg_latency_ms=1500,
                        max_context=100000
                    ),
                    quality_score=0.95,
                    description="High quality test provider",
                    created_at=datetime.now()
                )

            async def initialize(self, config: Dict[str, Any]) -> None:
                pass

            async def generate(self, prompt: str, **kwargs) -> str:
                return ""

            async def generate_streaming(self, prompt: str, **kwargs):
                yield ""

            async def generate_embeddings(self, text: str, **kwargs) -> List[float]:
                return []

            async def health_check(self) -> Dict[str, Any]:
                return {}

        ModelProviderRegistry.register("test-provider", MockProvider)

        # Get metadata
        metadata = ModelProviderRegistry.get_provider_metadata("test-provider")

        assert metadata is not None
        assert metadata.name == "Test Provider"
        assert metadata.quality_score == 0.95
        assert metadata.cost_profile.tier == CostTier.PREMIUM

    def test_get_providers_by_capability(self):
        """Test filtering providers by capability"""
        # Create providers with different capabilities
        class TextProvider(BaseModelProvider):
            def get_metadata(self) -> ModelMetadata:
                return ModelMetadata(
                    name="Text",
                    provider="text",
                    model_id="text-1",
                    version="1.0",
                    capabilities=ModelCapabilities.TEXT_GENERATION,
                    cost_profile=CostProfile(
                        tier=CostTier.STANDARD,
                        cost_per_1k_input=0.001,
                        cost_per_1k_output=0.002,
                        avg_latency_ms=1000,
                        max_context=4096
                    ),
                    quality_score=0.8,
                    description="Text only",
                    created_at=datetime.now()
                )

            async def initialize(self, config: Dict[str, Any]) -> None:
                pass

            async def generate(self, prompt: str, **kwargs) -> str:
                return ""

            async def generate_streaming(self, prompt: str, **kwargs):
                yield ""

            async def generate_embeddings(self, text: str, **kwargs) -> List[float]:
                return []

            async def health_check(self) -> Dict[str, Any]:
                return {}

        class VisionProvider(BaseModelProvider):
            def get_metadata(self) -> ModelMetadata:
                return ModelMetadata(
                    name="Vision",
                    provider="vision",
                    model_id="vision-1",
                    version="1.0",
                    capabilities=ModelCapabilities.TEXT_GENERATION | ModelCapabilities.VISION,
                    cost_profile=CostProfile(
                        tier=CostTier.PREMIUM,
                        cost_per_1k_input=0.005,
                        cost_per_1k_output=0.01,
                        avg_latency_ms=2000,
                        max_context=8192
                    ),
                    quality_score=0.9,
                    description="Vision capable",
                    created_at=datetime.now()
                )

            async def initialize(self, config: Dict[str, Any]) -> None:
                pass

            async def generate(self, prompt: str, **kwargs) -> str:
                return ""

            async def generate_streaming(self, prompt: str, **kwargs):
                yield ""

            async def generate_embeddings(self, text: str, **kwargs) -> List[float]:
                return []

            async def health_check(self) -> Dict[str, Any]:
                return {}

        ModelProviderRegistry.register("text-provider", TextProvider)
        ModelProviderRegistry.register("vision-provider", VisionProvider)

        # Find providers with vision capability
        vision_providers = ModelProviderRegistry.get_providers_by_capability(
            ModelCapabilities.VISION
        )

        assert "vision-provider" in vision_providers
        assert "text-provider" not in vision_providers


class TestModelSelector:
    """Test model selector with strategies"""

    def test_select_by_cost_strategy(self, monkeypatch):
        """Test cost-based selection strategy"""
        # Mock settings with test providers
        mock_settings = type('Settings', (), {
            'llm': type('LLM', (), {
                'selection_strategy': 'cost',
                'providers': {
                    'expensive': {
                        'enabled': True,
                        'cost_per_1k_input': 0.01,
                        'cost_per_1k_output': 0.02,
                        'cost_tier': 'premium',
                        'quality_score': 0.95,
                        'avg_latency_ms': 2000,
                        'max_context': 100000
                    },
                    'cheap': {
                        'enabled': True,
                        'cost_per_1k_input': 0.001,
                        'cost_per_1k_output': 0.002,
                        'cost_tier': 'economy',
                        'quality_score': 0.80,
                        'avg_latency_ms': 500,
                        'max_context': 10000
                    }
                },
                'task_model_overrides': {},
                'fallback_chain': ['expensive'],
                'default_provider': 'expensive'
            })()
        })()

        # Patch get_settings
        monkeypatch.setattr('src.services.llm.providers.model_selector.get_settings', lambda: mock_settings)

        selector = ModelSelector()
        selector.strategy = SelectionStrategy.COST

        # Select model with cost strategy
        selected = selector.select_model()

        assert selected == 'cheap'

    def test_select_by_quality_strategy(self, monkeypatch):
        """Test quality-based selection strategy"""
        # Mock settings
        mock_settings = type('Settings', (), {
            'llm': type('LLM', (), {
                'selection_strategy': 'quality',
                'providers': {
                    'high_quality': {
                        'enabled': True,
                        'cost_per_1k_input': 0.01,
                        'cost_per_1k_output': 0.02,
                        'cost_tier': 'premium',
                        'quality_score': 0.95,
                        'avg_latency_ms': 2000,
                        'max_context': 100000
                    },
                    'low_quality': {
                        'enabled': True,
                        'cost_per_1k_input': 0.001,
                        'cost_per_1k_output': 0.002,
                        'cost_tier': 'economy',
                        'quality_score': 0.70,
                        'avg_latency_ms': 500,
                        'max_context': 10000
                    }
                },
                'task_model_overrides': {},
                'fallback_chain': ['low_quality'],
                'default_provider': 'low_quality'
            })()
        })()

        monkeypatch.setattr('src.services.llm.providers.model_selector.get_settings', lambda: mock_settings)

        selector = ModelSelector()
        selector.strategy = SelectionStrategy.QUALITY

        # Select model with quality strategy
        selected = selector.select_model()

        assert selected == 'high_quality'

    def test_select_with_requirements(self, monkeypatch):
        """Test selection with specific requirements"""
        # Mock settings
        mock_settings = type('Settings', (), {
            'llm': type('LLM', (), {
                'selection_strategy': 'balanced',
                'providers': {
                    'fast': {
                        'enabled': True,
                        'cost_per_1k_input': 0.002,
                        'cost_per_1k_output': 0.004,
                        'cost_tier': 'standard',
                        'quality_score': 0.85,
                        'avg_latency_ms': 200,
                        'max_context': 50000,
                        'capabilities': 'text_generation,fast_inference'
                    },
                    'slow': {
                        'enabled': True,
                        'cost_per_1k_input': 0.003,
                        'cost_per_1k_output': 0.006,
                        'cost_tier': 'standard',
                        'quality_score': 0.90,
                        'avg_latency_ms': 3000,
                        'max_context': 100000,
                        'capabilities': 'text_generation'
                    }
                },
                'task_model_overrides': {},
                'fallback_chain': ['slow'],
                'default_provider': 'slow'
            })()
        })()

        monkeypatch.setattr('src.services.llm.providers.model_selector.get_settings', lambda: mock_settings)

        selector = ModelSelector()

        # Select with latency requirement
        requirements = TaskRequirements(
            max_latency_ms=500,
            max_cost_tier=CostTier.STANDARD
        )

        selected = selector.select_model(requirements=requirements)

        assert selected == 'fast'

    def test_manual_override_strategy(self, monkeypatch):
        """Test manual override strategy"""
        # Mock settings with task overrides
        mock_settings = type('Settings', (), {
            'llm': type('LLM', (), {
                'selection_strategy': 'manual',
                'providers': {
                    'default': {
                        'enabled': True,
                        'cost_per_1k_input': 0.002,
                        'cost_per_1k_output': 0.004,
                        'cost_tier': 'standard',
                        'quality_score': 0.85,
                        'avg_latency_ms': 1000,
                        'max_context': 50000
                    },
                    'override': {
                        'enabled': True,
                        'cost_per_1k_input': 0.003,
                        'cost_per_1k_output': 0.006,
                        'cost_tier': 'standard',
                        'quality_score': 0.80,
                        'avg_latency_ms': 1500,
                        'max_context': 40000
                    }
                },
                'task_model_overrides': {
                    'summarization': 'override'
                },
                'fallback_chain': ['default'],
                'default_provider': 'default'
            })()
        })()

        monkeypatch.setattr('src.services.llm.providers.model_selector.get_settings', lambda: mock_settings)

        selector = ModelSelector()
        selector.strategy = SelectionStrategy.MANUAL

        # Select with task type that has override
        selected = selector.select_model(task_type=LLMToolType.SUMMARIZATION)

        assert selected == 'override'

    def test_cost_estimation(self, monkeypatch):
        """Test cost estimation functionality"""
        # Mock settings
        mock_settings = type('Settings', (), {
            'llm': type('LLM', (), {
                'selection_strategy': 'cost',
                'providers': {
                    'test_model': {
                        'enabled': True,
                        'cost_per_1k_input': 0.003,
                        'cost_per_1k_output': 0.015,
                        'cost_tier': 'premium',
                        'quality_score': 0.95,
                        'avg_latency_ms': 2000,
                        'max_context': 100000
                    }
                },
                'task_model_overrides': {},
                'fallback_chain': ['test_model'],
                'default_provider': 'test_model'
            })()
        })()

        monkeypatch.setattr('src.services.llm.providers.model_selector.get_settings', lambda: mock_settings)

        selector = ModelSelector()

        # Estimate cost for 1000 input tokens and 500 output tokens
        cost = selector.estimate_cost('test_model', 1000, 500)

        # Should be (1000/1000 * 0.003) + (500/1000 * 0.015) = 0.003 + 0.0075 = 0.0105
        assert abs(cost - 0.0105) < 0.0001