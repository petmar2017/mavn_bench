"""Tests for StorageFactory"""

import pytest
from pathlib import Path

from src.storage.storage_factory import StorageFactory, StorageType
from src.storage.filesystem_storage import FilesystemStorage
from src.storage.redis_storage import RedisStorage
from src.storage.base_storage import StorageAdapter, StorageError


class TestStorageFactory:
    """Test suite for StorageFactory"""

    @pytest.fixture(autouse=True)
    def cleanup_factory(self):
        """Clean up factory instances after each test"""
        yield
        StorageFactory.clear_instances()

    @pytest.mark.asyncio
    async def test_create_filesystem_storage(self, temp_dir):
        """Test creating a filesystem storage instance"""
        storage = StorageFactory.create(
            StorageType.FILESYSTEM,
            base_path=str(temp_dir)
        )

        assert isinstance(storage, FilesystemStorage)
        assert storage.storage_type == "filesystem"
        assert storage.base_path == temp_dir

    @pytest.mark.asyncio
    async def test_create_redis_storage(self):
        """Test creating a Redis storage instance"""
        storage = StorageFactory.create(
            StorageType.REDIS,
            redis_url="redis://localhost:6379/1"
        )

        assert isinstance(storage, RedisStorage)
        assert storage.storage_type == "redis"
        assert storage.redis_url == "redis://localhost:6379/1"

    @pytest.mark.asyncio
    async def test_singleton_pattern(self, temp_dir):
        """Test that singleton pattern works correctly"""
        # Create first instance
        storage1 = StorageFactory.create(
            StorageType.FILESYSTEM,
            singleton=True,
            base_path=str(temp_dir)
        )

        # Create second instance with same type
        storage2 = StorageFactory.create(
            StorageType.FILESYSTEM,
            singleton=True
        )

        # Should be the same instance
        assert storage1 is storage2

    @pytest.mark.asyncio
    async def test_non_singleton_creation(self, temp_dir):
        """Test creating non-singleton instances"""
        # Create first instance
        storage1 = StorageFactory.create(
            StorageType.FILESYSTEM,
            singleton=False,
            base_path=str(temp_dir / "storage1")
        )

        # Create second instance
        storage2 = StorageFactory.create(
            StorageType.FILESYSTEM,
            singleton=False,
            base_path=str(temp_dir / "storage2")
        )

        # Should be different instances
        assert storage1 is not storage2
        assert storage1.base_path != storage2.base_path

    @pytest.mark.asyncio
    async def test_create_with_default_config(self, monkeypatch):
        """Test creating storage with default configuration"""
        # Mock settings to return filesystem type
        def mock_get_settings():
            class MockSettings:
                class StorageConfig:
                    type = "filesystem"
                    filesystem_base_path = "/tmp/test_storage"
                    redis_url = "redis://localhost:6379"
                storage = StorageConfig()
            return MockSettings()

        monkeypatch.setattr("src.storage.storage_factory.get_settings", mock_get_settings)

        # Create without specifying type
        storage = StorageFactory.create()

        assert isinstance(storage, FilesystemStorage)
        assert storage.storage_type == "filesystem"

    @pytest.mark.asyncio
    async def test_get_default(self, monkeypatch):
        """Test getting default storage adapter"""
        def mock_get_settings():
            class MockSettings:
                class StorageConfig:
                    type = "filesystem"
                    filesystem_base_path = "/tmp/test_storage"
                storage = StorageConfig()
            return MockSettings()

        monkeypatch.setattr("src.storage.storage_factory.get_settings", mock_get_settings)

        storage = StorageFactory.get_default()

        assert isinstance(storage, FilesystemStorage)

    @pytest.mark.asyncio
    async def test_unknown_storage_type(self):
        """Test creating unknown storage type raises error"""
        with pytest.raises(StorageError, match="Unknown storage type"):
            StorageFactory.create("unknown_type")

    @pytest.mark.asyncio
    async def test_register_custom_storage(self):
        """Test registering a custom storage adapter"""

        class CustomStorage(StorageAdapter):
            """Custom storage implementation for testing"""

            def __init__(self):
                super().__init__("custom")

            async def save(self, document):
                return True

            async def load(self, document_id):
                return None

            async def delete(self, document_id):
                return True

            async def exists(self, document_id):
                return False

            async def list_documents(self, **kwargs):
                return []

            async def save_version(self, document_id, version):
                return True

            async def get_versions(self, document_id):
                return []

            async def revert_to_version(self, document_id, version_number):
                return None

            async def health_check(self):
                return {"status": "healthy"}

        # Register custom storage
        custom_type = "custom"
        StorageFactory.register(custom_type, CustomStorage)

        # Create instance
        storage = StorageFactory.create(custom_type)

        assert isinstance(storage, CustomStorage)
        assert storage.storage_type == "custom"

    @pytest.mark.asyncio
    async def test_clear_instances(self, temp_dir):
        """Test clearing all singleton instances"""
        # Create multiple instances
        fs_storage = StorageFactory.create(
            StorageType.FILESYSTEM,
            base_path=str(temp_dir)
        )
        redis_storage = StorageFactory.create(
            StorageType.REDIS,
            redis_url="redis://localhost:6379/1"
        )

        # Clear instances
        StorageFactory.clear_instances()

        # Create new instances - should be different objects
        new_fs_storage = StorageFactory.create(
            StorageType.FILESYSTEM,
            base_path=str(temp_dir)
        )

        assert new_fs_storage is not fs_storage

    @pytest.mark.asyncio
    async def test_get_available_types(self):
        """Test getting list of available storage types"""
        types = StorageFactory.get_available_types()

        assert StorageType.FILESYSTEM in types
        assert StorageType.REDIS in types
        assert len(types) >= 2

    @pytest.mark.asyncio
    async def test_hybrid_storage_not_implemented(self):
        """Test that hybrid storage raises NotImplementedError"""
        from src.storage.storage_factory import HybridStorage

        hybrid = HybridStorage()

        with pytest.raises(NotImplementedError):
            await hybrid.save(None)

        with pytest.raises(NotImplementedError):
            await hybrid.load("test")

        with pytest.raises(NotImplementedError):
            await hybrid.delete("test")

        with pytest.raises(NotImplementedError):
            await hybrid.exists("test")

        with pytest.raises(NotImplementedError):
            await hybrid.list_documents()

        with pytest.raises(NotImplementedError):
            await hybrid.save_version("test", None)

        with pytest.raises(NotImplementedError):
            await hybrid.get_versions("test")

        with pytest.raises(NotImplementedError):
            await hybrid.revert_to_version("test", 1)

        with pytest.raises(NotImplementedError):
            await hybrid.health_check()

    @pytest.mark.asyncio
    async def test_factory_error_handling(self):
        """Test error handling in factory creation"""

        class FailingStorage(StorageAdapter):
            """Storage that fails on initialization"""

            def __init__(self):
                raise Exception("Initialization failed")

        # Register failing storage
        StorageFactory.register("failing", FailingStorage)

        # Should raise StorageError
        with pytest.raises(StorageError, match="Failed to create storage"):
            StorageFactory.create("failing")

    @pytest.mark.asyncio
    async def test_config_defaults_applied(self, monkeypatch, temp_dir):
        """Test that configuration defaults are properly applied"""

        def mock_get_settings():
            class MockSettings:
                class StorageConfig:
                    type = "filesystem"
                    filesystem_base_path = str(temp_dir)
                    redis_url = "redis://custom:6380"
                storage = StorageConfig()
            return MockSettings()

        monkeypatch.setattr("src.storage.storage_factory.get_settings", mock_get_settings)

        # Create filesystem without specifying path
        fs_storage = StorageFactory.create(
            StorageType.FILESYSTEM,
            singleton=False
        )
        assert str(fs_storage.base_path) == str(temp_dir)

        # Create Redis without specifying URL
        redis_storage = StorageFactory.create(
            StorageType.REDIS,
            singleton=False
        )
        assert redis_storage.redis_url == "redis://custom:6380"