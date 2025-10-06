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


def scan_and_import_providers(
    package_path: str = "src.services.llm.providers.implementations"
) -> List[str]:
    """Scan and import all provider modules to trigger decorator registration

    This function dynamically imports all provider modules in the specified package
    to ensure their @register_provider decorators are executed.

    Args:
        package_path: Python package path containing provider modules

    Returns:
        List of imported module names
    """
    import importlib
    from pathlib import Path

    imported_modules = []

    try:
        # Get the implementations directory
        base_path = Path(__file__).parent / "implementations"

        if not base_path.exists():
            return imported_modules

        # Import all Python files ending with _providers.py
        for file_path in base_path.glob("*_providers.py"):
            if file_path.name.startswith("__"):
                continue  # Skip __init__.py and __pycache__

            module_name = file_path.stem
            full_module_path = f"{package_path}.{module_name}"

            try:
                importlib.import_module(full_module_path)
                imported_modules.append(full_module_path)
            except ImportError as e:
                # Log warning but continue with other modules
                print(f"Warning: Could not import provider module {full_module_path}: {e}")

    except Exception as e:
        print(f"Error scanning provider modules: {e}")

    return imported_modules


def initialize_providers() -> Dict[str, Any]:
    """Initialize the provider system by scanning and registering all providers

    This is the main initialization function that should be called during
    application startup. It:
    1. Scans for provider modules and imports them
    2. Registers all decorated providers
    3. Returns initialization statistics

    Returns:
        Dictionary with initialization statistics
    """
    from typing import Any

    # Scan and import provider modules
    imported_modules = scan_and_import_providers()

    # Register all decorated providers
    registered_count = auto_register_decorated_providers()

    # Get registry statistics
    from .provider_registry import ModelProviderRegistry
    provider_count = len(ModelProviderRegistry._providers)

    return {
        "imported_modules": imported_modules,
        "imported_module_count": len(imported_modules),
        "registered_providers": registered_count,
        "total_providers": provider_count,
    }