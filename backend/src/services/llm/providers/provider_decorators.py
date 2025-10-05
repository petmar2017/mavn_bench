"""Decorator-based registration for model providers"""

from typing import Type, Optional, List, Dict
from .base_provider import BaseModelProvider
from .provider_registry import ModelProviderRegistry


# Dictionary to hold decorated providers before registration
_decorated_providers: Dict[str, Type[BaseModelProvider]] = {}


def register_provider(
    provider_name: str,
    aliases: Optional[List[str]] = None
):
    """Decorator to register a model provider

    Args:
        provider_name: Unique name for the provider
        aliases: Optional list of alternative names

    Returns:
        Decorator function
    """
    def decorator(cls: Type[BaseModelProvider]) -> Type[BaseModelProvider]:
        """Inner decorator"""
        # Store in decorated providers dict
        _decorated_providers[provider_name] = cls

        # Also register aliases
        if aliases:
            for alias in aliases:
                _decorated_providers[alias] = cls

        # Mark class with metadata
        cls._provider_name = provider_name
        cls._provider_aliases = aliases or []

        return cls

    return decorator


def auto_register_decorated_providers() -> int:
    """Auto-register all decorated providers

    This function is called during service initialization to
    register all providers that were decorated with @register_provider

    Returns:
        Number of providers registered
    """
    count = 0
    for provider_name, provider_class in _decorated_providers.items():
        ModelProviderRegistry.register(provider_name, provider_class)
        count += 1

    return count