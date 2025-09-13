"""Storage module for Mavn Bench"""

from .base_storage import (
    StorageAdapter,
    StorageError,
    DocumentNotFoundError,
    StorageConnectionError,
    VersionNotFoundError
)
from .filesystem_storage import FilesystemStorage
from .redis_storage import RedisStorage
from .storage_factory import StorageFactory, StorageType

__all__ = [
    # Base classes and exceptions
    "StorageAdapter",
    "StorageError",
    "DocumentNotFoundError",
    "StorageConnectionError",
    "VersionNotFoundError",

    # Storage implementations
    "FilesystemStorage",
    "RedisStorage",

    # Factory
    "StorageFactory",
    "StorageType",
]