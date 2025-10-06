"""Redis storage adapter implementation"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import redis.asyncio as redis
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

from .base_storage import (
    StorageAdapter,
    StorageError,
    DocumentNotFoundError,
    StorageConnectionError,
    VersionNotFoundError
)
from ..models.document import DocumentMessage, DocumentMetadata, DocumentVersion
from ..core.config import get_settings


class RedisStorage(StorageAdapter):
    """Redis-based storage adapter for caching and fast access"""

    def __init__(self, redis_url: Optional[str] = None):
        """Initialize Redis storage

        Args:
            redis_url: Redis connection URL
        """
        super().__init__("redis")
        settings = get_settings()
        self.redis_url = redis_url or settings.storage.redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.key_prefix = "mavn_bench"
        self.ttl_seconds = 86400  # 24 hours default TTL

        self.logger.info(f"Initialized Redis storage with URL: {self.redis_url}")

    async def _ensure_connected(self):
        """Ensure Redis connection is established"""
        if not self.redis_client:
            try:
                self.redis_client = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                # Test connection
                await self.redis_client.ping()
                self.logger.info("Connected to Redis successfully")
            except (RedisError, RedisConnectionError) as e:
                self.logger.error(f"Failed to connect to Redis: {str(e)}")
                raise StorageConnectionError(f"Redis connection failed: {str(e)}") from e

    def _get_document_key(self, document_id: str) -> str:
        """Get Redis key for a document"""
        return f"{self.key_prefix}:document:{document_id}"

    def _get_metadata_key(self, document_id: str) -> str:
        """Get Redis key for document metadata"""
        return f"{self.key_prefix}:metadata:{document_id}"

    def _get_version_key(self, document_id: str, version: int) -> str:
        """Get Redis key for a document version"""
        return f"{self.key_prefix}:version:{document_id}:{version}"

    def _get_versions_list_key(self, document_id: str) -> str:
        """Get Redis key for versions list"""
        return f"{self.key_prefix}:versions:{document_id}"

    def _get_document_list_key(self) -> str:
        """Get Redis key for document list"""
        return f"{self.key_prefix}:documents"


    def _get_file_key(self, document_id: str, extension: str) -> str:
        """Get Redis key for original file"""
        return f"{self.key_prefix}:file:{document_id}{extension}"

    def _get_file_info_key(self, document_id: str, extension: str) -> str:
        """Get Redis key for file metadata"""
        return f"{self.key_prefix}:file:{document_id}{extension}:info"

    async def save(self, document: DocumentMessage) -> bool:
        """Save a document to Redis"""
        with self.traced_operation("save", document_id=document.metadata.document_id):
            await self._ensure_connected()

            try:
                document_id = document.metadata.document_id
                document_key = self._get_document_key(document_id)
                metadata_key = self._get_metadata_key(document_id)
                list_key = self._get_document_list_key()

                # Serialize document and metadata
                document_data = document.model_dump(mode="json")
                document_json = json.dumps(document_data, default=str)

                metadata_data = document.metadata.model_dump(mode="json")
                metadata_json = json.dumps(metadata_data, default=str)

                # Use pipeline for atomic operations
                pipe = self.redis_client.pipeline()

                # Save document with TTL
                pipe.setex(document_key, self.ttl_seconds, document_json)

                # Save metadata with TTL
                pipe.setex(metadata_key, self.ttl_seconds, metadata_json)

                # Add to document list (sorted set with timestamp as score)
                timestamp = datetime.utcnow().timestamp()
                pipe.zadd(list_key, {document_id: timestamp})

                # Save initial version if it's a new document
                if document.metadata.version == 1:
                    version = DocumentVersion(
                        version=1,
                        timestamp=datetime.utcnow(),
                        user=document.metadata.created_user,
                        changes={"action": "created"},
                        commit_message="Initial version"
                    )
                    version_key = self._get_version_key(document_id, 1)
                    version_json = json.dumps(version.model_dump(mode="json"), default=str)
                    pipe.setex(version_key, self.ttl_seconds, version_json)

                    # Add to versions list
                    versions_key = self._get_versions_list_key(document_id)
                    pipe.lpush(versions_key, 1)
                    pipe.expire(versions_key, self.ttl_seconds)

                # Execute pipeline
                await pipe.execute()

                self.logger.debug(f"Saved document {document_id} to Redis with TTL {self.ttl_seconds}s")
                return True

            except RedisError as e:
                self.logger.error(f"Failed to save document {document_id} to Redis: {str(e)}")
                raise StorageError(f"Redis save failed: {str(e)}") from e

    async def load(self, document_id: str) -> Optional[DocumentMessage]:
        """Load a document from Redis"""
        with self.traced_operation("load", document_id=document_id):
            await self._ensure_connected()

            try:
                document_key = self._get_document_key(document_id)
                document_json = await self.redis_client.get(document_key)

                if not document_json:
                    self.logger.debug(f"Document {document_id} not found in Redis")
                    return None

                document_data = json.loads(document_json)
                document = DocumentMessage(**document_data)

                # Refresh TTL on access
                await self.redis_client.expire(document_key, self.ttl_seconds)

                self.logger.debug(f"Loaded document {document_id} from Redis")
                return document

            except json.JSONDecodeError as e:
                self.logger.error(f"Invalid JSON in document {document_id}: {str(e)}")
                raise StorageError(f"Invalid document format: {str(e)}") from e
            except RedisError as e:
                self.logger.error(f"Failed to load document {document_id} from Redis: {str(e)}")
                raise StorageError(f"Redis load failed: {str(e)}") from e

    async def delete(self, document_id: str) -> bool:
        """Delete a document from Redis"""
        with self.traced_operation("delete", document_id=document_id):
            await self._ensure_connected()

            try:
                document_key = self._get_document_key(document_id)
                metadata_key = self._get_metadata_key(document_id)
                versions_key = self._get_versions_list_key(document_id)
                list_key = self._get_document_list_key()

                # Get all version keys
                version_numbers = await self.redis_client.lrange(versions_key, 0, -1)
                version_keys = [
                    self._get_version_key(document_id, int(v))
                    for v in version_numbers if v
                ]

                # Use pipeline for atomic deletion
                pipe = self.redis_client.pipeline()

                # Delete document and metadata
                pipe.delete(document_key)
                pipe.delete(metadata_key)

                # Delete from document list
                pipe.zrem(list_key, document_id)

                # Delete versions
                for version_key in version_keys:
                    pipe.delete(version_key)
                pipe.delete(versions_key)

                # Execute pipeline
                results = await pipe.execute()

                # Check if document was actually deleted (first delete operation)
                deleted = bool(results[0])

                if deleted:
                    self.logger.info(f"Deleted document {document_id} from Redis")
                else:
                    self.logger.warning(f"Document {document_id} not found in Redis for deletion")

                return deleted

            except RedisError as e:
                self.logger.error(f"Failed to delete document {document_id} from Redis: {str(e)}")
                raise StorageError(f"Redis delete failed: {str(e)}") from e

    async def exists(self, document_id: str) -> bool:
        """Check if a document exists in Redis"""
        with self.traced_operation("exists", document_id=document_id):
            await self._ensure_connected()

            try:
                document_key = self._get_document_key(document_id)
                exists = await self.redis_client.exists(document_key)
                self.logger.debug(f"Document {document_id} exists in Redis: {bool(exists)}")
                return bool(exists)

            except RedisError as e:
                self.logger.error(f"Failed to check existence of document {document_id}: {str(e)}")
                raise StorageError(f"Redis exists check failed: {str(e)}") from e

    async def list_documents(
        self,
        user_id: Optional[str] = None,
        document_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[DocumentMessage]:
        """List documents with optional filtering"""
        with self.traced_operation(
            "list_documents",
            user_id=user_id,
            document_type=document_type,
            limit=limit,
            offset=offset
        ):
            await self._ensure_connected()

            try:
                list_key = self._get_document_list_key()

                # Get all document IDs (sorted by timestamp)
                document_ids = await self.redis_client.zrevrange(
                    list_key, 0, -1
                )

                document_list = []

                for doc_id in document_ids:
                    metadata_key = self._get_metadata_key(doc_id)
                    metadata_json = await self.redis_client.get(metadata_key)

                    if not metadata_json:
                        continue

                    metadata_data = json.loads(metadata_json)
                    metadata = DocumentMetadata(**metadata_data)

                    # Apply filters
                    if user_id and metadata.created_user != user_id:
                        continue
                    if document_type and metadata.document_type != document_type:
                        continue

                    # Load the full document
                    document = await self.load(doc_id)
                    if document:
                        document_list.append(document)

                # Apply pagination
                start = offset
                end = offset + limit
                paginated_list = document_list[start:end]

                self.logger.info(
                    f"Listed {len(paginated_list)} documents from Redis "
                    f"(total: {len(document_list)}, offset: {offset}, limit: {limit})"
                )
                return paginated_list

            except RedisError as e:
                self.logger.error(f"Failed to list documents from Redis: {str(e)}")
                raise StorageError(f"Redis list failed: {str(e)}") from e

    async def save_version(
        self,
        document_id: str,
        version: DocumentVersion
    ) -> bool:
        """Save a document version to Redis"""
        with self.traced_operation(
            "save_version",
            document_id=document_id,
            version=version.version
        ):
            await self._ensure_connected()

            try:
                version_key = self._get_version_key(document_id, version.version)
                versions_key = self._get_versions_list_key(document_id)

                # Serialize version
                version_data = version.model_dump(mode="json")
                version_json = json.dumps(version_data, default=str)

                # Use pipeline for atomic operations
                pipe = self.redis_client.pipeline()

                # Save version with TTL
                pipe.setex(version_key, self.ttl_seconds, version_json)

                # Add to versions list if not already present
                existing_versions = await self.redis_client.lrange(versions_key, 0, -1)
                if str(version.version) not in existing_versions:
                    pipe.lpush(versions_key, version.version)
                    pipe.expire(versions_key, self.ttl_seconds)

                # Execute pipeline
                await pipe.execute()

                self.logger.info(f"Saved version {version.version} for document {document_id} to Redis")
                return True

            except RedisError as e:
                self.logger.error(f"Failed to save version to Redis: {str(e)}")
                raise StorageError(f"Redis version save failed: {str(e)}") from e

    async def get_versions(
        self,
        document_id: str
    ) -> List[DocumentVersion]:
        """Get all versions of a document from Redis"""
        with self.traced_operation("get_versions", document_id=document_id):
            await self._ensure_connected()

            try:
                versions_key = self._get_versions_list_key(document_id)
                version_numbers = await self.redis_client.lrange(versions_key, 0, -1)

                if not version_numbers:
                    self.logger.debug(f"No versions found for document {document_id} in Redis")
                    return []

                versions = []

                for version_num in sorted(version_numbers, key=int):
                    version_key = self._get_version_key(document_id, int(version_num))
                    version_json = await self.redis_client.get(version_key)

                    if version_json:
                        version_data = json.loads(version_json)
                        versions.append(DocumentVersion(**version_data))

                self.logger.info(f"Retrieved {len(versions)} versions for document {document_id} from Redis")
                return versions

            except RedisError as e:
                self.logger.error(f"Failed to get versions from Redis: {str(e)}")
                raise StorageError(f"Redis get versions failed: {str(e)}") from e

    async def revert_to_version(
        self,
        document_id: str,
        version_number: int
    ) -> Optional[DocumentMessage]:
        """Revert a document to a specific version"""
        with self.traced_operation(
            "revert_to_version",
            document_id=document_id,
            version=version_number
        ):
            await self._ensure_connected()

            try:
                # Check if version exists
                version_key = self._get_version_key(document_id, version_number)
                version_json = await self.redis_client.get(version_key)

                if not version_json:
                    self.logger.warning(f"Version {version_number} not found for document {document_id}")
                    raise VersionNotFoundError(f"Version {version_number} not found")

                # Load the current document
                current_doc = await self.load(document_id)
                if not current_doc:
                    raise DocumentNotFoundError(f"Document {document_id} not found")

                # Create a new version entry for the revert action
                new_version = current_doc.metadata.version + 1
                revert_version = DocumentVersion(
                    version=new_version,
                    timestamp=datetime.utcnow(),
                    user=current_doc.metadata.updated_user,
                    changes={
                        "action": "reverted",
                        "reverted_to": version_number
                    },
                    commit_message=f"Reverted to version {version_number}"
                )

                # Update document metadata
                current_doc.metadata.version = new_version
                current_doc.metadata.updated_timestamp = datetime.utcnow()
                current_doc.history.append(revert_version)

                # Save the reverted document
                await self.save(current_doc)
                await self.save_version(document_id, revert_version)

                self.logger.info(f"Reverted document {document_id} to version {version_number}")
                return current_doc

            except RedisError as e:
                self.logger.error(f"Failed to revert document in Redis: {str(e)}")
                raise StorageError(f"Redis revert failed: {str(e)}") from e

    async def list_all(self) -> List[str]:
        """List all document IDs in storage

        Returns:
            List of all document IDs
        """
        with self.traced_operation("list_all"):
            try:
                await self._ensure_connected()

                # Get all document IDs from the sorted set
                list_key = self._get_document_list_key()
                documents = await self.redis_client.zrange(list_key, 0, -1)

                # Decode document IDs
                document_ids = [doc_id.decode() if isinstance(doc_id, bytes) else doc_id for doc_id in documents]

                self.logger.info(f"Found {len(document_ids)} documents in Redis storage")
                return document_ids

            except RedisError as e:
                self.logger.error(f"Failed to list documents in Redis: {str(e)}")
                raise StorageError(f"Failed to list documents: {str(e)}") from e

    async def health_check(self) -> Dict[str, Any]:
        """Check Redis storage health"""
        with self.traced_operation("health_check"):
            try:
                await self._ensure_connected()

                # Ping Redis
                ping_response = await self.redis_client.ping()

                # Get Redis info
                info = await self.redis_client.info()

                # Count documents
                list_key = self._get_document_list_key()
                document_count = await self.redis_client.zcard(list_key)

                health_status = {
                    "status": "healthy" if ping_response else "unhealthy",
                    "storage_type": self.storage_type,
                    "redis_url": self.redis_url,
                    "connected": bool(ping_response),
                    "document_count": document_count,
                    "redis_version": info.get("redis_version", "unknown"),
                    "used_memory_human": info.get("used_memory_human", "unknown"),
                    "connected_clients": info.get("connected_clients", 0)
                }

                self.logger.info(f"Redis health check: {health_status['status']}")
                return health_status

            except (RedisError, RedisConnectionError) as e:
                self.logger.error(f"Redis health check failed: {str(e)}")
                return {
                    "status": "error",
                    "storage_type": self.storage_type,
                    "error": str(e)
                }

    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
            self.logger.info("Closed Redis connection")


    async def save_file(
        self,
        document_id: str,
        file_content: bytes,
        extension: str = ""
    ) -> str:
        """Save original uploaded file to Redis with base64 encoding

        Args:
            document_id: Document ID
            file_content: File content as bytes
            extension: File extension (e.g., ".pdf")

        Returns:
            Relative file path

        Raises:
            StorageError: If save fails or file too large
        """
        with self.traced_operation("save_file", document_id=document_id):
            await self._ensure_connected()

            try:
                # Enforce file size limit for Redis (10MB)
                max_size = 10 * 1024 * 1024  # 10MB
                if len(file_content) > max_size:
                    raise StorageError(
                        f"File too large for Redis storage: {len(file_content)} bytes "
                        f"(max: {max_size} bytes). Use filesystem storage for large files."
                    )

                file_key = self._get_file_key(document_id, extension)
                info_key = self._get_file_info_key(document_id, extension)

                # Encode binary content as base64 for Redis storage
                import base64
                encoded_content = base64.b64encode(file_content).decode('utf-8')

                # Create file metadata
                file_info = {
                    "size": len(file_content),
                    "extension": extension,
                    "timestamp": datetime.utcnow().isoformat(),
                    "encoding": "base64"
                }

                # Use pipeline for atomic operations
                pipe = self.redis_client.pipeline()

                # Save file with TTL
                pipe.setex(file_key, self.ttl_seconds, encoded_content)

                # Save file info with TTL
                pipe.setex(info_key, self.ttl_seconds, json.dumps(file_info))

                # Execute pipeline
                await pipe.execute()

                relative_path = f"files/{document_id}{extension}"
                self.logger.info(
                    f"Saved file to Redis: {relative_path} "
                    f"(size: {len(file_content)} bytes, TTL: {self.ttl_seconds}s)"
                )
                return relative_path

            except RedisError as e:
                self.logger.error(f"Failed to save file to Redis: {str(e)}")
                raise StorageError(f"Redis file save failed: {str(e)}") from e

    async def get_file(
        self,
        document_id: str,
        extension: str = ""
    ) -> Optional[bytes]:
        """Retrieve original uploaded file from Redis

        Args:
            document_id: Document ID
            extension: File extension (e.g., ".pdf")

        Returns:
            File content as bytes, or None if not found

        Raises:
            StorageError: If retrieval fails
        """
        with self.traced_operation("get_file", document_id=document_id):
            await self._ensure_connected()

            try:
                file_key = self._get_file_key(document_id, extension)

                # Check if key exists (handles empty files)
                exists = await self.redis_client.exists(file_key)
                if not exists:
                    self.logger.debug(f"File not found in Redis: {document_id}{extension}")
                    return None

                encoded_content = await self.redis_client.get(file_key)

                # Decode base64 to binary (handles empty string)
                import base64
                file_content = base64.b64decode(encoded_content) if encoded_content else b""

                # Refresh TTL on access
                await self.redis_client.expire(file_key, self.ttl_seconds)

                self.logger.info(
                    f"Retrieved file from Redis: {document_id}{extension} "
                    f"(size: {len(file_content)} bytes)"
                )
                return file_content

            except Exception as e:
                self.logger.error(f"Failed to retrieve file from Redis: {str(e)}")
                raise StorageError(f"Redis file retrieval failed: {str(e)}") from e

    async def delete_file(
        self,
        document_id: str,
        extension: str = ""
    ) -> bool:
        """Delete original uploaded file from Redis

        Args:
            document_id: Document ID
            extension: File extension (e.g., ".pdf")

        Returns:
            True if successful, False otherwise

        Raises:
            StorageError: If deletion fails
        """
        with self.traced_operation("delete_file", document_id=document_id):
            await self._ensure_connected()

            try:
                file_key = self._get_file_key(document_id, extension)
                info_key = self._get_file_info_key(document_id, extension)

                # Delete file and info atomically
                pipe = self.redis_client.pipeline()
                pipe.delete(file_key)
                pipe.delete(info_key)
                results = await pipe.execute()

                # Check if file was actually deleted (first delete operation)
                deleted = bool(results[0])

                if deleted:
                    self.logger.info(f"Deleted file from Redis: {document_id}{extension}")
                else:
                    self.logger.debug(f"File not found for deletion: {document_id}{extension}")

                return deleted

            except RedisError as e:
                self.logger.error(f"Failed to delete file from Redis: {str(e)}")
                raise StorageError(f"Redis file delete failed: {str(e)}") from e
