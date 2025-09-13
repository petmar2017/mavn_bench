"""Service factory for creating service instances"""

from typing import Type, Dict, Any, Optional
from enum import Enum

from .base_service import BaseService
from ..core.logger import CentralizedLogger
from ..storage.storage_factory import StorageFactory, StorageType


class ServiceType(str, Enum):
    """Supported service types"""
    DOCUMENT = "document"
    PDF = "pdf"
    TRANSCRIPTION = "transcription"
    WEB_SCRAPING = "web_scraping"
    LLM = "llm"
    VECTOR_SEARCH = "vector_search"
    GRAPH_SEARCH = "graph_search"
    FULLTEXT_SEARCH = "fulltext_search"
    MCP_REGISTRY = "mcp_registry"
    MCP_PROXY = "mcp_proxy"


class ServiceFactory:
    """Factory for creating service instances with dependency injection"""

    _services: Dict[ServiceType, Type[BaseService]] = {}
    _instances: Dict[ServiceType, BaseService] = {}
    _logger = CentralizedLogger("ServiceFactory")

    @classmethod
    def register(cls, service_type: ServiceType, service_class: Type[BaseService]):
        """Register a service class

        Args:
            service_type: Type identifier for the service
            service_class: Service class to register
        """
        cls._services[service_type] = service_class
        cls._logger.info(f"Registered service: {service_type}")

    @classmethod
    def create(
        cls,
        service_type: ServiceType,
        singleton: bool = True,
        **kwargs
    ) -> BaseService:
        """Create or get singleton service instance

        Args:
            service_type: Type of service to create
            singleton: Whether to use singleton pattern (default: True)
            **kwargs: Additional arguments to pass to service constructor

        Returns:
            Service instance

        Raises:
            ValueError: If service type is unknown
        """
        # Check for existing instance if singleton
        if singleton and service_type in cls._instances:
            cls._logger.debug(f"Returning existing {service_type} instance")
            return cls._instances[service_type]

        # Create new instance
        service_class = cls._services.get(service_type)
        if not service_class:
            raise ValueError(f"Unknown service type: {service_type}")

        # Inject storage dependency if not provided
        if "storage" not in kwargs:
            kwargs["storage"] = StorageFactory.get_default()
            cls._logger.debug(f"Injected default storage for {service_type}")

        try:
            instance = service_class(**kwargs)

            # Store instance if singleton
            if singleton:
                cls._instances[service_type] = instance

            cls._logger.info(
                f"Created {service_type} service instance "
                f"(singleton: {singleton})"
            )
            return instance

        except Exception as e:
            cls._logger.error(f"Failed to create {service_type} service: {str(e)}")
            raise

    @classmethod
    def get_all_instances(cls) -> Dict[ServiceType, BaseService]:
        """Get all singleton instances

        Returns:
            Dictionary of service instances
        """
        return cls._instances.copy()

    @classmethod
    def clear_instances(cls):
        """Clear all singleton instances (mainly for testing)"""
        # Call cleanup on services if they have it
        for service_type, instance in cls._instances.items():
            if hasattr(instance, "cleanup"):
                try:
                    instance.cleanup()
                except Exception as e:
                    cls._logger.warning(f"Error cleaning up {service_type}: {str(e)}")

        cls._instances.clear()
        cls._logger.info("Cleared all service instances")

    @classmethod
    def get_available_services(cls) -> list[ServiceType]:
        """Get list of registered service types

        Returns:
            List of available service types
        """
        return list(cls._services.keys())

    @classmethod
    async def health_check_all(cls) -> Dict[str, Any]:
        """Run health checks on all active services

        Returns:
            Health status for all services
        """
        health_status = {}

        for service_type, instance in cls._instances.items():
            try:
                health = await instance.health_check()
                health_status[service_type] = health
            except Exception as e:
                health_status[service_type] = {
                    "status": "error",
                    "error": str(e)
                }

        return health_status