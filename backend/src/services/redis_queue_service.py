"""Redis-based queue service for distributed document processing

This service implements a distributed queue using Redis to enable horizontal
scaling of document processing workers. It uses DocumentMessage objects
stored in Redis with atomic operations for thread-safe queue management.
"""

import json
import uuid
import asyncio
from typing import Optional, List, Dict, Any, Set
from datetime import datetime, timedelta
import redis.asyncio as redis
from redis.exceptions import RedisError, LockError

from ..models.document import DocumentMessage, ProcessingStage
from ..core.config import get_settings
from ..core.logger import CentralizedLogger
from ..storage.storage_factory import StorageFactory, StorageType
from .base_service import BaseService


class RedisQueueService(BaseService):
    """Redis-based distributed queue for document processing

    This service manages a distributed queue using Redis sorted sets
    for priority-based processing with atomic operations. It supports:
    - Horizontal scaling with multiple workers
    - Atomic dequeue operations to prevent duplicate processing
    - Priority-based processing with timestamps
    - Retry mechanism with exponential backoff
    - Dead letter queue for failed documents
    - Worker heartbeat and stale job recovery
    """

    # Redis key prefixes
    QUEUE_KEY = "mavn_bench:queue:pending"
    PROCESSING_KEY = "mavn_bench:queue:processing"
    FAILED_KEY = "mavn_bench:queue:failed"
    WORKER_KEY = "mavn_bench:workers"
    LOCK_KEY = "mavn_bench:locks"

    # Processing timeouts
    DEFAULT_PROCESSING_TIMEOUT = 300  # 5 minutes
    WORKER_HEARTBEAT_INTERVAL = 30    # 30 seconds
    STALE_WORKER_TIMEOUT = 120        # 2 minutes

    def __init__(self, redis_url: Optional[str] = None):
        """Initialize Redis queue service

        Args:
            redis_url: Redis connection URL (defaults to config)
        """
        super().__init__("RedisQueueService")
        settings = get_settings()
        self.redis_url = redis_url or settings.storage.redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.worker_id = str(uuid.uuid4())
        self.storage = None
        self.heartbeat_task = None
        self.logger.info(f"Initialized Redis queue service with worker ID: {self.worker_id}")

    async def _ensure_connected(self):
        """Ensure Redis connection is established"""
        if not self.redis_client:
            try:
                self.redis_client = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                await self.redis_client.ping()
                self.logger.info("Connected to Redis for queue management")

                # Initialize storage adapter for document operations
                if not self.storage:
                    self.storage = StorageFactory.create(
                        StorageType.REDIS if "redis" in self.redis_url else StorageType.FILESYSTEM
                    )

                # Start worker heartbeat
                if not self.heartbeat_task:
                    self.heartbeat_task = asyncio.create_task(self._worker_heartbeat())

            except RedisError as e:
                self.logger.error(f"Failed to connect to Redis: {str(e)}")
                raise

    async def _worker_heartbeat(self):
        """Send periodic heartbeat to indicate worker is alive"""
        while True:
            try:
                await asyncio.sleep(self.WORKER_HEARTBEAT_INTERVAL)
                if self.redis_client:
                    worker_key = f"{self.WORKER_KEY}:{self.worker_id}"
                    await self.redis_client.setex(
                        worker_key,
                        self.STALE_WORKER_TIMEOUT,
                        json.dumps({
                            "worker_id": self.worker_id,
                            "last_heartbeat": datetime.utcnow().isoformat(),
                            "status": "active"
                        })
                    )
            except Exception as e:
                self.logger.error(f"Worker heartbeat failed: {str(e)}")

    async def enqueue(self, document: DocumentMessage, priority: Optional[float] = None) -> bool:
        """Add a document to the processing queue

        Args:
            document: Document to process
            priority: Optional priority (lower = higher priority, default: timestamp)

        Returns:
            True if successfully enqueued
        """
        with self.traced_operation("enqueue", document_id=document.metadata.document_id):
            await self._ensure_connected()

            try:
                document_id = document.metadata.document_id

                # Update document status to PENDING
                document.metadata.processing_stage = ProcessingStage.PENDING
                # Store processing timestamps separately in Redis (not in metadata)

                # Save document to storage
                await self.storage.save(document)

                # Add to queue with priority (default: timestamp for FIFO)
                if priority is None:
                    priority = datetime.utcnow().timestamp()

                # Add document ID to pending queue sorted set
                await self.redis_client.zadd(
                    self.QUEUE_KEY,
                    {document_id: priority}
                )

                self.logger.info(f"Enqueued document {document_id} with priority {priority}")
                return True

            except Exception as e:
                self.logger.error(f"Failed to enqueue document: {str(e)}")
                return False

    async def dequeue(self, batch_size: int = 1) -> Optional[List[DocumentMessage]]:
        """Atomically dequeue documents for processing

        Uses Redis ZPOPMIN for atomic dequeue operation to prevent
        multiple workers from processing the same document.

        Args:
            batch_size: Number of documents to dequeue (default: 1)

        Returns:
            List of documents to process, or None if queue is empty
        """
        with self.traced_operation("dequeue", batch_size=batch_size):
            await self._ensure_connected()

            try:
                # Atomically pop documents from pending queue
                results = await self.redis_client.zpopmin(self.QUEUE_KEY, batch_size)

                if not results:
                    return None

                documents = []
                processing_timestamp = datetime.utcnow().timestamp()

                for document_id, priority in results:
                    # Load document from storage
                    document = await self.storage.load(document_id)

                    if not document:
                        self.logger.warning(f"Document {document_id} not found in storage")
                        continue

                    # Update status to PROCESSING
                    document.metadata.processing_stage = ProcessingStage.PROCESSING

                    # Store processing metadata in Redis separately (not in document metadata)
                    start_time = datetime.utcnow()
                    await self.redis_client.set(
                        f"processing_started:{document_id}",
                        start_time.isoformat(),
                        ex=86400  # 1 day TTL
                    )
                    await self.redis_client.set(
                        f"processor_id:{document_id}",
                        self.worker_id,
                        ex=86400  # 1 day TTL
                    )

                    # Save updated status
                    await self.storage.save(document)

                    # Add to processing set with timeout timestamp
                    processing_data = json.dumps({
                        "worker_id": self.worker_id,
                        "started_at": start_time.isoformat(),
                        "timeout_at": (start_time + timedelta(seconds=self.DEFAULT_PROCESSING_TIMEOUT)).isoformat()
                    })

                    await self.redis_client.hset(
                        self.PROCESSING_KEY,
                        document_id,
                        processing_data
                    )

                    documents.append(document)
                    self.logger.info(f"Dequeued document {document_id} for processing by worker {self.worker_id}")

                return documents if documents else None

            except Exception as e:
                self.logger.error(f"Failed to dequeue documents: {str(e)}")
                return None

    async def mark_completed(self, document_id: str) -> bool:
        """Mark a document as successfully processed

        Args:
            document_id: ID of completed document

        Returns:
            True if successfully marked as completed
        """
        with self.traced_operation("mark_completed", document_id=document_id):
            await self._ensure_connected()

            try:
                # Load document
                document = await self.storage.load(document_id)
                if not document:
                    self.logger.error(f"Document {document_id} not found")
                    return False

                # Update status to COMPLETED
                document.metadata.processing_stage = ProcessingStage.COMPLETED

                # Store completion time in Redis separately
                completion_time = datetime.utcnow()
                await self.redis_client.set(
                    f"processing_completed:{document_id}",
                    completion_time.isoformat(),
                    ex=86400  # 1 day TTL
                )

                # Get start time from Redis if available
                start_time_str = await self.redis_client.get(f"processing_started:{document_id}")
                if start_time_str:
                    start_time = datetime.fromisoformat(start_time_str)
                    duration = (completion_time - start_time).total_seconds()
                    self.logger.info(f"Document {document_id} processed in {duration:.2f} seconds")

                # Save updated document
                await self.storage.save(document)

                # Remove from processing set
                await self.redis_client.hdel(self.PROCESSING_KEY, document_id)

                self.logger.info(f"Marked document {document_id} as completed")
                return True

            except Exception as e:
                self.logger.error(f"Failed to mark document as completed: {str(e)}")
                return False

    async def mark_failed(self, document_id: str, error: str, retry: bool = True) -> bool:
        """Mark a document as failed with optional retry

        Args:
            document_id: ID of failed document
            error: Error message
            retry: Whether to retry processing (default: True)

        Returns:
            True if successfully marked as failed
        """
        with self.traced_operation("mark_failed", document_id=document_id, retry=retry):
            await self._ensure_connected()

            try:
                # Load document
                document = await self.storage.load(document_id)
                if not document:
                    self.logger.error(f"Document {document_id} not found")
                    return False

                # Get retry count from Redis (not from metadata)
                retry_key = f"retry_count:{document_id}"
                current_retry = await self.redis_client.get(retry_key)
                retry_count = int(current_retry) + 1 if current_retry else 1

                # Store updated retry count in Redis
                await self.redis_client.set(retry_key, str(retry_count), ex=86400)  # 1 day TTL

                # Store error in Redis separately (last_error doesn't exist in metadata)
                await self.redis_client.set(
                    f"last_error:{document_id}",
                    error,
                    ex=86400  # 1 day TTL
                )

                # Store processing completion time in Redis
                completion_time = datetime.utcnow()
                await self.redis_client.set(
                    f"processing_completed:{document_id}",
                    completion_time.isoformat(),
                    ex=86400  # 1 day TTL
                )

                # Remove from processing set
                await self.redis_client.hdel(self.PROCESSING_KEY, document_id)

                # Determine if we should retry
                max_retries = 3
                if retry and retry_count < max_retries:
                    # Calculate exponential backoff
                    backoff_seconds = min(300, 10 * (2 ** retry_count))  # Max 5 minutes
                    priority = datetime.utcnow().timestamp() + backoff_seconds

                    # Update status back to PENDING for retry
                    document.metadata.processing_stage = ProcessingStage.PENDING
                    await self.storage.save(document)

                    # Re-enqueue with lower priority (higher timestamp)
                    await self.redis_client.zadd(self.QUEUE_KEY, {document_id: priority})

                    self.logger.warning(
                        f"Document {document_id} failed (attempt {retry_count}/{max_retries}), "
                        f"retrying in {backoff_seconds} seconds: {error}"
                    )
                else:
                    # Move to failed queue (dead letter queue)
                    document.metadata.processing_stage = ProcessingStage.FAILED
                    await self.storage.save(document)

                    failed_data = json.dumps({
                        "document_id": document_id,
                        "error": error,
                        "retry_count": retry_count,
                        "failed_at": datetime.utcnow().isoformat(),
                        "worker_id": self.worker_id
                    })

                    await self.redis_client.zadd(
                        self.FAILED_KEY,
                        {document_id: datetime.utcnow().timestamp()}
                    )

                    self.logger.error(
                        f"Document {document_id} failed permanently after {retry_count} attempts: {error}"
                    )

                return True

            except Exception as e:
                self.logger.error(f"Failed to mark document as failed: {str(e)}")
                return False

    async def recover_stale_jobs(self) -> int:
        """Recover jobs from workers that have stopped heartbeating

        Returns:
            Number of jobs recovered
        """
        with self.traced_operation("recover_stale_jobs"):
            await self._ensure_connected()

            try:
                recovered = 0

                # Get all processing jobs
                processing_jobs = await self.redis_client.hgetall(self.PROCESSING_KEY)

                for document_id, job_data in processing_jobs.items():
                    try:
                        job_info = json.loads(job_data)
                        timeout_at = datetime.fromisoformat(job_info["timeout_at"])
                        worker_id = job_info["worker_id"]

                        # Check if job has timed out
                        if datetime.utcnow() > timeout_at:
                            # Check if worker is still alive
                            worker_key = f"{self.WORKER_KEY}:{worker_id}"
                            worker_status = await self.redis_client.get(worker_key)

                            if not worker_status:
                                # Worker is dead, recover the job
                                self.logger.warning(
                                    f"Recovering stale job {document_id} from dead worker {worker_id}"
                                )

                                # Remove from processing
                                await self.redis_client.hdel(self.PROCESSING_KEY, document_id)

                                # Re-enqueue for processing
                                await self.redis_client.zadd(
                                    self.QUEUE_KEY,
                                    {document_id: datetime.utcnow().timestamp()}
                                )

                                # Update document status
                                document = await self.storage.load(document_id)
                                if document:
                                    document.metadata.processing_stage = ProcessingStage.PENDING
                                    # Store error in Redis separately (last_error doesn't exist in metadata)
                                    await self.redis_client.set(
                                        f"last_error:{document_id}",
                                        f"Worker {worker_id} timed out",
                                        ex=86400  # 1 day TTL
                                    )
                                    await self.storage.save(document)

                                recovered += 1

                    except Exception as e:
                        self.logger.error(f"Error recovering job {document_id}: {str(e)}")

                if recovered > 0:
                    self.logger.info(f"Recovered {recovered} stale jobs")

                return recovered

            except Exception as e:
                self.logger.error(f"Failed to recover stale jobs: {str(e)}")
                return 0

    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get current queue statistics

        Returns:
            Dictionary with queue stats
        """
        with self.traced_operation("get_queue_stats"):
            await self._ensure_connected()

            try:
                pending_count = await self.redis_client.zcard(self.QUEUE_KEY)
                processing_count = await self.redis_client.hlen(self.PROCESSING_KEY)
                failed_count = await self.redis_client.zcard(self.FAILED_KEY)

                # Get active workers
                worker_pattern = f"{self.WORKER_KEY}:*"
                worker_keys = await self.redis_client.keys(worker_pattern)
                active_workers = len(worker_keys)

                # Get processing details
                processing_jobs = await self.redis_client.hgetall(self.PROCESSING_KEY)
                processing_details = []

                for doc_id, job_data in processing_jobs.items():
                    try:
                        job_info = json.loads(job_data)
                        processing_details.append({
                            "document_id": doc_id,
                            "worker_id": job_info["worker_id"],
                            "started_at": job_info["started_at"],
                            "timeout_at": job_info["timeout_at"]
                        })
                    except:
                        pass

                return {
                    "pending": pending_count,
                    "processing": processing_count,
                    "failed": failed_count,
                    "active_workers": active_workers,
                    "worker_id": self.worker_id,
                    "processing_details": processing_details
                }

            except Exception as e:
                self.logger.error(f"Failed to get queue stats: {str(e)}")
                return {
                    "pending": 0,
                    "processing": 0,
                    "failed": 0,
                    "active_workers": 0,
                    "error": str(e)
                }

    async def clear_queue(self, queue_type: str = "all") -> bool:
        """Clear specified queue(s)

        Args:
            queue_type: "pending", "processing", "failed", or "all"

        Returns:
            True if successfully cleared
        """
        with self.traced_operation("clear_queue", queue_type=queue_type):
            await self._ensure_connected()

            try:
                if queue_type in ["pending", "all"]:
                    await self.redis_client.delete(self.QUEUE_KEY)
                    self.logger.info("Cleared pending queue")

                if queue_type in ["processing", "all"]:
                    await self.redis_client.delete(self.PROCESSING_KEY)
                    self.logger.info("Cleared processing queue")

                if queue_type in ["failed", "all"]:
                    await self.redis_client.delete(self.FAILED_KEY)
                    self.logger.info("Cleared failed queue")

                return True

            except Exception as e:
                self.logger.error(f"Failed to clear queue: {str(e)}")
                return False

    async def requeue_failed(self) -> int:
        """Requeue all failed documents for retry

        Returns:
            Number of documents requeued
        """
        with self.traced_operation("requeue_failed"):
            await self._ensure_connected()

            try:
                # Get all failed documents
                failed_docs = await self.redis_client.zrange(self.FAILED_KEY, 0, -1)

                if not failed_docs:
                    return 0

                # Requeue each document
                for document_id in failed_docs:
                    document = await self.storage.load(document_id)
                    if document:
                        # Reset retry count and status
                        document.metadata.retry_count = 0
                        document.metadata.processing_stage = ProcessingStage.PENDING
                        document.metadata.last_error = None
                        await self.storage.save(document)

                        # Add to pending queue
                        await self.redis_client.zadd(
                            self.QUEUE_KEY,
                            {document_id: datetime.utcnow().timestamp()}
                        )

                # Clear failed queue
                await self.redis_client.delete(self.FAILED_KEY)

                self.logger.info(f"Requeued {len(failed_docs)} failed documents")
                return len(failed_docs)

            except Exception as e:
                self.logger.error(f"Failed to requeue failed documents: {str(e)}")
                return 0

    async def health_check(self) -> Dict[str, Any]:
        """Check Redis queue health

        Returns:
            Health status dictionary
        """
        with self.traced_operation("health_check"):
            try:
                await self._ensure_connected()

                # Get queue stats
                stats = await self.get_queue_stats()

                # Check Redis connection
                ping_response = await self.redis_client.ping()

                return {
                    "service": "RedisQueueService",
                    "status": "healthy" if ping_response else "unhealthy",
                    "worker_id": self.worker_id,
                    "redis_connected": bool(ping_response),
                    "queue_stats": stats
                }

            except Exception as e:
                self.logger.error(f"Health check failed: {str(e)}")
                return {
                    "service": "RedisQueueService",
                    "status": "error",
                    "error": str(e)
                }

    async def close(self):
        """Close Redis connections and stop heartbeat"""
        try:
            # Stop heartbeat task
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
                try:
                    await self.heartbeat_task
                except asyncio.CancelledError:
                    pass

            # Remove worker from active list
            if self.redis_client:
                worker_key = f"{self.WORKER_KEY}:{self.worker_id}"
                await self.redis_client.delete(worker_key)

                # Close Redis connection
                await self.redis_client.close()
                self.redis_client = None

            self.logger.info(f"Closed Redis queue service for worker {self.worker_id}")

        except Exception as e:
            self.logger.error(f"Error closing Redis queue service: {str(e)}")