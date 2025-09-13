"""Storage factory for creating storage adapter instances"""

from typing import Type, Dict, Optional, Any
from enum import Enum

from .base_storage import StorageAdapter, StorageError
from .filesystem_storage import FilesystemStorage
from .redis_storage import RedisStorage
from ..core.logger import CentralizedLogger
from ..core.config import get_settings


class StorageType(str, Enum):
    """Supported storage backend types"""
    FILESYSTEM = "filesystem"
    REDIS = "redis"
    HYBRID = "hybrid"  # Future: Combined filesystem + Redis


class StorageFactory:
    """Factory for creating storage adapter instances with dependency injection"""

    _storage_classes: Dict[StorageType, Type[StorageAdapter]] = {
        StorageType.FILESYSTEM: FilesystemStorage,
        StorageType.REDIS: RedisStorage,
    }

    _instances: Dict[StorageType, StorageAdapter] = {}
    _logger = CentralizedLogger("StorageFactory")

    @classmethod
    def register(cls, storage_type: StorageType, storage_class: Type[StorageAdapter]):
        """Register a custom storage adapter class

        Args:
            storage_type: Type identifier for the storage
            storage_class: Storage adapter class to register
        """
        cls._storage_classes[storage_type] = storage_class
        cls._logger.info(f"Registered storage adapter: {storage_type}")

    @classmethod
    def create(
        cls,
        storage_type: Optional[StorageType] = None,
        singleton: bool = True,
        **kwargs
    ) -> StorageAdapter:
        """Create or get a storage adapter instance

        Args:
            storage_type: Type of storage to create (uses config default if None)
            singleton: Whether to use singleton pattern (default: True)
            **kwargs: Additional arguments to pass to storage constructor

        Returns:
            Storage adapter instance

        Raises:
            StorageError: If storage type is unknown or creation fails
        """
        # Use configuration default if not specified
        if storage_type is None:
            settings = get_settings()
            storage_type = StorageType(settings.storage.type)
            cls._logger.info(f"Using configured storage type: {storage_type}")

        # Validate storage type
        if storage_type not in cls._storage_classes:
            raise StorageError(f"Unknown storage type: {storage_type}")

        # Return existing instance if singleton
        if singleton and storage_type in cls._instances:
            cls._logger.debug(f"Returning existing {storage_type} instance")
            return cls._instances[storage_type]

        # Create new instance
        try:
            storage_class = cls._storage_classes[storage_type]

            # Apply default configuration based on storage type
            if storage_type == StorageType.FILESYSTEM and "base_path" not in kwargs:
                settings = get_settings()
                kwargs["base_path"] = settings.storage.filesystem_base_path
            elif storage_type == StorageType.REDIS and "redis_url" not in kwargs:
                settings = get_settings()
                kwargs["redis_url"] = settings.storage.redis_url

            instance = storage_class(**kwargs)

            # Store instance if singleton
            if singleton:
                cls._instances[storage_type] = instance

            cls._logger.info(
                f"Created {storage_type} storage instance "
                f"(singleton: {singleton})"
            )
            return instance

        except Exception as e:
            cls._logger.error(f"Failed to create {storage_type} storage: {str(e)}")
            raise StorageError(f"Failed to create storage: {str(e)}") from e

    @classmethod
    def get_default(cls) -> StorageAdapter:
        """Get the default storage adapter based on configuration

        Returns:
            Default storage adapter instance
        """
        return cls.create()

    @classmethod
    def clear_instances(cls):
        """Clear all singleton instances (mainly for testing)"""
        # Close any Redis connections before clearing
        for storage_type, instance in cls._instances.items():
            if storage_type == StorageType.REDIS and hasattr(instance, "close"):
                import asyncio
                try:
                    asyncio.run(instance.close())
                except Exception as e:
                    cls._logger.warning(f"Error closing {storage_type} storage: {str(e)}")

        cls._instances.clear()
        cls._logger.info("Cleared all storage instances")

    @classmethod
    def get_available_types(cls) -> list[StorageType]:
        """Get list of available storage types

        Returns:
            List of registered storage types
        """
        return list(cls._storage_classes.keys())


class HybridStorage(StorageAdapter):
    """Hybrid storage adapter combining filesystem and Redis (future implementation)

    This will use Redis for hot data and filesystem for cold data,
    with automatic promotion/demotion based on access patterns.
    """

    def __init__(self, filesystem_path: Optional[str] = None, redis_url: Optional[str] = None):
        """Initialize hybrid storage

        Args:
            filesystem_path: Base path for filesystem storage
            redis_url: Redis connection URL
        """
        super().__init__("hybrid")
        self.filesystem = FilesystemStorage(filesystem_path)
        self.redis = RedisStorage(redis_url)
        self.logger.info("Initialized hybrid storage (filesystem + Redis)")

    async def save(self, document: Any) -> bool:
        """Save to both storages (Redis as cache, filesystem as persistent)"""
        # Implementation would save to both, with Redis as write-through cache
        raise NotImplementedError("Hybrid storage not yet implemented")

    async def load(self, document_id: str) -> Optional[Any]:
        """Load from Redis first, fallback to filesystem"""
        # Implementation would check Redis first, then filesystem
        raise NotImplementedError("Hybrid storage not yet implemented")

    async def delete(self, document_id: str) -> bool:
        """Delete from both storages"""
        raise NotImplementedError("Hybrid storage not yet implemented")

    async def exists(self, document_id: str) -> bool:
        """Check existence in either storage"""
        raise NotImplementedError("Hybrid storage not yet implemented")

    async def list_documents(
        self,
        user_id: Optional[str] = None,
        document_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list:
        """List documents from filesystem (source of truth)"""
        raise NotImplementedError("Hybrid storage not yet implemented")

    async def save_version(self, document_id: str, version: Any) -> bool:
        """Save version to filesystem only"""
        raise NotImplementedError("Hybrid storage not yet implemented")

    async def get_versions(self, document_id: str) -> list:
        """Get versions from filesystem"""
        raise NotImplementedError("Hybrid storage not yet implemented")

    async def revert_to_version(self, document_id: str, version_number: int) -> Optional[Any]:
        """Revert using filesystem versions"""
        raise NotImplementedError("Hybrid storage not yet implemented")

    async def health_check(self) -> Dict[str, Any]:
        """Check health of both storages"""
        raise NotImplementedError("Hybrid storage not yet implemented")