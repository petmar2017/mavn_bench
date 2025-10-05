"""Registry for model providers with auto-discovery"""

from typing import Dict, Type, Optional, List, Any
from ....core.logger import CentralizedLogger
from .base_provider import BaseModelProvider, ModelMetadata


class ModelProviderRegistry:
    """Registry for managing model providers

    This class provides a central registry for all LLM model providers,
    allowing dynamic registration and discovery of providers.
    Similar to ToolRegistry but for model providers.
    """

    _providers: Dict[str, Type[BaseModelProvider]] = {}
    _instances: Dict[str, BaseModelProvider] = {}
    _logger = CentralizedLogger("ModelProviderRegistry")

    @classmethod
    def register(cls, provider_name: str, provider_class: Type[BaseModelProvider]):
        """Register a provider class

        Args:
            provider_name: Unique identifier for the provider
            provider_class: Provider class to register
        """
        if not issubclass(provider_class, BaseModelProvider):
            raise ValueError(f"{provider_class} must inherit from BaseModelProvider")

        cls._providers[provider_name] = provider_class
        cls._logger.info(f"Registered model provider: {provider_name}")

    @classmethod
    async def create(
        cls,
        provider_name: str,
        config: Optional[Dict[str, Any]] = None,
        singleton: bool = True
    ) -> BaseModelProvider:
        """Create or get a provider instance

        Args:
            provider_name: Name of the provider to create
            config: Configuration for the provider
            singleton: If True, reuse existing instances

        Returns:
            Provider instance

        Raises:
            ValueError: If provider not found
        """
        if provider_name not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ValueError(
                f"Provider '{provider_name}' not found. "
                f"Available providers: {available}"
            )

        # Return singleton if exists and requested
        if singleton and provider_name in cls._instances:
            return cls._instances[provider_name]

        # Create new instance
        provider_class = cls._providers[provider_name]
        provider = provider_class()

        # Initialize with config
        if config:
            await provider.initialize(config)

        # Store singleton
        if singleton:
            cls._instances[provider_name] = provider

        cls._logger.debug(f"Created provider instance: {provider_name}")
        return provider

    @classmethod
    def get_available_providers(cls) -> List[str]:
        """Get list of available provider names

        Returns:
            List of registered provider names
        """
        return list(cls._providers.keys())

    @classmethod
    def get_provider_metadata(cls, provider_name: str) -> Optional[ModelMetadata]:
        """Get metadata for a provider

        Args:
            provider_name: Name of the provider

        Returns:
            Provider metadata or None if not found
        """
        if provider_name not in cls._providers:
            return None

        # Create temporary instance to get metadata
        provider_class = cls._providers[provider_name]
        provider = provider_class()
        return provider.get_metadata()

    @classmethod
    def get_providers_by_capability(cls, *capabilities) -> List[str]:
        """Find providers that support specific capabilities

        Args:
            *capabilities: Capabilities to filter by

        Returns:
            List of provider names that support all specified capabilities
        """
        matching_providers = []

        for provider_name in cls._providers:
            metadata = cls.get_provider_metadata(provider_name)
            if metadata:
                # Check if provider has all requested capabilities
                has_all = all(
                    metadata.capabilities & cap
                    for cap in capabilities
                )
                if has_all:
                    matching_providers.append(provider_name)

        return matching_providers

    @classmethod
    def get_provider_info(cls) -> Dict[str, Dict[str, Any]]:
        """Get information about all providers

        Returns:
            Dictionary with provider information
        """
        info = {}

        for provider_name in cls._providers:
            metadata = cls.get_provider_metadata(provider_name)
            if metadata:
                info[provider_name] = {
                    "name": metadata.name,
                    "provider": metadata.provider,
                    "model_id": metadata.model_id,
                    "version": metadata.version,
                    "capabilities": [
                        cap.name for cap in metadata.capabilities.__class__
                        if metadata.capabilities & cap
                    ],
                    "cost_tier": metadata.cost_profile.tier.value,
                    "max_context": metadata.cost_profile.max_context,
                    "quality_score": metadata.quality_score,
                    "description": metadata.description,
                    "deprecated": metadata.deprecated
                }

        return info

    @classmethod
    def clear(cls):
        """Clear all registered providers (mainly for testing)"""
        cls._providers.clear()
        cls._instances.clear()
        cls._logger.debug("Cleared all registered providers")

    @classmethod
    async def shutdown_all(cls):
        """Shutdown all provider instances"""
        for provider in cls._instances.values():
            await provider.shutdown()
        cls._instances.clear()
        cls._logger.info("Shutdown all provider instances")