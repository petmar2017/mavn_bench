"""
Queue Service for managing document processing queue.

This service handles:
- Document queue management
- Job tracking and status updates
- Queue position tracking
- WebSocket notifications for status changes
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import deque
import json

from src.services.base_service import BaseService
from src.models.document import ProcessingStage, DocumentType, DocumentMessage
from src.core.logger import CentralizedLogger
from src.storage.storage_factory import StorageFactory, StorageType
from src.core.config import get_settings
from .redis_queue_service import RedisQueueService

logger = CentralizedLogger(__name__)


class ProcessingJob:
    """Represents a document processing job in the queue."""

    def __init__(
        self,
        job_id: str,
        document_id: str,
        user_id: str,
        file_path: str,
        file_type: str,
        metadata: Dict[str, Any]
    ):
        self.job_id = job_id
        self.document_id = document_id
        self.user_id = user_id
        self.file_path = file_path
        self.file_type = file_type
        self.metadata = metadata
        self.status = ProcessingStage.PENDING
        self.progress = 0
        self.queue_position = 0
        self.created_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for API responses."""
        return {
            "job_id": self.job_id,
            "document_id": self.document_id,
            "user_id": self.user_id,
            "status": self.status.value,
            "progress": self.progress,
            "queue_position": self.queue_position,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message
        }


class QueueService(BaseService):
    """Service for managing document processing queue."""

    def __init__(self):
        super().__init__("QueueService")
        self.settings = get_settings()
        self._websocket_service = None  # Will be injected
        self._processing_task: Optional[asyncio.Task] = None
        self._stale_job_check_task: Optional[asyncio.Task] = None

        # Initialize based on backend configuration
        if self.settings.queue.backend == "redis":
            try:
                self.redis_queue = RedisQueueService()
                self.use_redis_queue = True
                self.max_concurrent_jobs = self.settings.queue.max_concurrent_workers
                logger.info("QueueService using Redis backend for distributed processing")
            except Exception as e:
                logger.warning(f"Redis backend failed, falling back to memory: {e}")
                self._init_memory_queue()
        else:
            self._init_memory_queue()

    def _init_memory_queue(self):
        """Initialize in-memory queue for fallback or when configured"""
        self.use_redis_queue = False
        self.redis_queue = None
        self.queue: deque[ProcessingJob] = deque()
        self.active_jobs: Dict[str, ProcessingJob] = {}
        self.completed_jobs: Dict[str, ProcessingJob] = {}
        self.job_by_document: Dict[str, ProcessingJob] = {}
        self.processing_lock = asyncio.Lock()
        self.max_concurrent_jobs = self.settings.queue.max_concurrent_workers
        self.current_processing = 0

        # Try to use Redis storage for document persistence
        try:
            self.storage = StorageFactory.create(StorageType.REDIS)
        except Exception as e:
            logger.warning(f"Redis storage initialization failed: {e}")
            self.storage = None

        logger.info("QueueService using in-memory backend")

    def set_websocket_service(self, websocket_service):
        """Inject WebSocket service for real-time updates."""
        self._websocket_service = websocket_service

    async def start_processing(self):
        """Start the background processing task."""
        if self.use_redis_queue:
            # Start Redis-based processing
            if not self._processing_task or self._processing_task.done():
                self._processing_task = asyncio.create_task(self._process_redis_queue())
                logger.info("Redis queue processing started")

            # Start stale job recovery task
            if not self._stale_job_check_task or self._stale_job_check_task.done():
                self._stale_job_check_task = asyncio.create_task(self._check_stale_jobs())
                logger.info("Stale job recovery task started")
        else:
            # Start memory-based processing
            if not self._processing_task or self._processing_task.done():
                self._processing_task = asyncio.create_task(self._process_queue())
                logger.info("Memory queue processing started")

    async def stop_processing(self):
        """Stop the background processing task."""
        tasks_to_cancel = []

        if self._processing_task and not self._processing_task.done():
            tasks_to_cancel.append(self._processing_task)

        if self._stale_job_check_task and not self._stale_job_check_task.done():
            tasks_to_cancel.append(self._stale_job_check_task)

        for task in tasks_to_cancel:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Close Redis queue if used
        if self.use_redis_queue and self.redis_queue:
            await self.redis_queue.close()

        logger.info("Queue processing stopped")

    async def enqueue_document(
        self,
        document_id: str,
        user_id: str,
        file_path: str,
        file_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a document to the processing queue.

        Returns:
            job_id: Unique identifier for the processing job
        """
        with self.traced_operation("enqueue_document", document_id=document_id):
            if self.use_redis_queue:
                # Use Redis queue for distributed processing
                # Load the document from storage
                storage = StorageFactory.create(StorageType.REDIS)
                document = await storage.load(document_id)

                if not document:
                    raise ValueError(f"Document {document_id} not found in storage")

                # Store file path in document metadata for processing
                document.metadata.file_path = file_path
                document.metadata.processing_stage = ProcessingStage.PENDING

                # Enqueue in Redis
                success = await self.redis_queue.enqueue(document)

                if success:
                    logger.info(f"Document {document_id} enqueued in Redis queue")

                    # Ensure processing is running
                    await self.start_processing()

                    return document_id  # Use document_id as job_id for Redis queue
                else:
                    raise RuntimeError(f"Failed to enqueue document {document_id}")
            else:
                # Use in-memory queue
                job_id = str(uuid.uuid4())

                job = ProcessingJob(
                    job_id=job_id,
                    document_id=document_id,
                    user_id=user_id,
                    file_path=file_path,
                    file_type=file_type,
                    metadata=metadata or {}
                )

                async with self.processing_lock:
                    self.queue.append(job)
                    job.queue_position = len(self.queue)
                    self.active_jobs[job_id] = job
                    self.job_by_document[document_id] = job

                    # Update queue positions
                    self._update_queue_positions()

                # Send WebSocket notification
                await self._notify_job_queued(job)

                logger.info(f"Document {document_id} queued with job_id {job_id}, position {job.queue_position}")

                # Ensure processing is running
                await self.start_processing()

                return job_id

    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a processing job."""
        # Check active jobs
        if job_id in self.active_jobs:
            return self.active_jobs[job_id].to_dict()

        # Check completed jobs
        if job_id in self.completed_jobs:
            return self.completed_jobs[job_id].to_dict()

        # Check Redis if available
        if self.use_redis:
            job_data = await self._load_job(job_id)
            if job_data:
                return job_data

        return None

    async def get_queue_position(self, job_id: str) -> Optional[int]:
        """Get the queue position for a job."""
        if job_id in self.active_jobs:
            return self.active_jobs[job_id].queue_position
        return None

    async def get_user_jobs(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all jobs for a specific user."""
        user_jobs = []

        # Active jobs
        for job in self.active_jobs.values():
            if job.user_id == user_id:
                user_jobs.append(job.to_dict())

        # Completed jobs
        for job in self.completed_jobs.values():
            if job.user_id == user_id:
                user_jobs.append(job.to_dict())

        # Sort by created_at
        user_jobs.sort(key=lambda x: x['created_at'], reverse=True)

        return user_jobs

    async def get_queue_status(self) -> Dict[str, Any]:
        """Get overall queue status."""
        if self.use_redis_queue:
            # Get status from Redis queue
            stats = await self.redis_queue.get_queue_stats()
            return {
                "backend": "redis",
                "queue_length": stats.get("pending", 0),
                "processing": stats.get("processing", 0),
                "failed": stats.get("failed", 0),
                "max_concurrent": self.max_concurrent_jobs,
                "active_workers": stats.get("active_workers", 0),
                "worker_id": stats.get("worker_id", "unknown")
            }
        else:
            # Get status from memory queue
            return {
                "backend": "memory",
                "queue_length": len(self.queue),
                "processing": self.current_processing,
                "max_concurrent": self.max_concurrent_jobs,
                "active_jobs": len(self.active_jobs),
                "completed_jobs": len(self.completed_jobs)
            }

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a queued job."""
        async with self.processing_lock:
            if job_id in self.active_jobs:
                job = self.active_jobs[job_id]

                # Only cancel if still pending
                if job.status == ProcessingStage.PENDING:
                    # Remove from queue
                    try:
                        self.queue.remove(job)
                    except ValueError:
                        pass

                    # Mark as failed
                    job.status = ProcessingStage.FAILED
                    job.error_message = "Cancelled by user"
                    job.completed_at = datetime.utcnow()

                    # Move to completed
                    self.completed_jobs[job_id] = job
                    del self.active_jobs[job_id]

                    # Update queue positions
                    self._update_queue_positions()

                    # Notify
                    await self._notify_job_cancelled(job)

                    logger.info(f"Job {job_id} cancelled")
                    return True

        return False

    async def _process_queue(self):
        """Background task to process the queue."""
        logger.info("Queue processor started")

        while True:
            try:
                # Check if we can process more jobs
                if self.current_processing >= self.max_concurrent_jobs or not self.queue:
                    await asyncio.sleep(1)
                    continue

                async with self.processing_lock:
                    if not self.queue:
                        continue

                    # Get next job
                    job = self.queue.popleft()
                    self.current_processing += 1

                    # Update queue positions
                    self._update_queue_positions()

                # Process the job
                asyncio.create_task(self._process_job(job))

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in queue processor: {e}")
                await asyncio.sleep(5)

    async def _process_job(self, job: ProcessingJob):
        """Process a single job."""
        try:
            # Update job status
            job.status = ProcessingStage.PROCESSING
            job.started_at = datetime.utcnow()
            job.queue_position = 0

            # Notify job started
            await self._notify_job_started(job)

            # Import here to avoid circular dependency
            from src.services.service_factory import ServiceFactory, ServiceType
            from src.services.document_service import DocumentService
            from src.models.document import DocumentType
            import aiofiles

            # Get services
            doc_service = DocumentService()
            pdf_service = ServiceFactory.create(ServiceType.PDF)
            llm_service = ServiceFactory.create(ServiceType.LLM)

            job.progress = 10
            await self._notify_job_progress(job)

            # Process based on file type
            formatted_content = ""
            raw_text = ""

            if job.file_type == DocumentType.PDF.value:
                # Convert PDF to markdown
                markdown_content = await pdf_service.pdf_to_markdown(job.file_path)
                job.progress = 30
                await self._notify_job_progress(job)

                # Skip LLM validation for now - it's causing processing to hang
                # TODO: Re-enable once LLM service is properly configured
                formatted_content = markdown_content
                raw_text = markdown_content
                job.progress = 50
                await self._notify_job_progress(job)

                logger.info(f"PDF processed without LLM validation: {job.document_id}")

            elif job.file_type in [DocumentType.WORD.value, DocumentType.TEXT.value]:
                # For Word and text files, extract text and convert to markdown
                async with aiofiles.open(job.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    raw_text = await f.read()

                job.progress = 30
                await self._notify_job_progress(job)

                # Use LLM to format as markdown with proper error handling
                try:
                    # Set a timeout for LLM processing
                    formatted_content = await asyncio.wait_for(
                        llm_service.text_to_markdown(raw_text[:10000]),  # Limit input
                        timeout=30.0  # 30 second timeout
                    )
                    logger.info(f"Text file processed with LLM formatting: {job.document_id}")
                except asyncio.TimeoutError:
                    logger.warning(f"LLM text_to_markdown timed out for {job.document_id}, using raw text")
                    formatted_content = raw_text
                except Exception as e:
                    logger.warning(f"LLM text_to_markdown failed for {job.document_id}: {str(e)}, using raw text")
                    formatted_content = raw_text

                job.progress = 50
                await self._notify_job_progress(job)
            else:
                # For other types, read as text
                async with aiofiles.open(job.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    raw_text = await f.read()
                formatted_content = raw_text
                job.progress = 50
                await self._notify_job_progress(job)

            # Detect language and generate summary with proper timeouts
            language = "en"  # Default
            summary = None

            try:
                # Detect language with timeout
                lang_result = await asyncio.wait_for(
                    llm_service.detect_language(raw_text[:1000]),
                    timeout=10.0  # 10 second timeout
                )
                language = lang_result[0] if lang_result and lang_result[0] != "unknown" else "en"
                job.progress = 70
                await self._notify_job_progress(job)
                logger.info(f"Language detected for {job.document_id}: {language}")
            except asyncio.TimeoutError:
                logger.warning(f"Language detection timed out for {job.document_id}, using default: en")
                language = "en"
            except Exception as e:
                logger.warning(f"Language detection failed for {job.document_id}: {str(e)}, using default: en")
                language = "en"

            try:
                # Generate summary with timeout
                summary = await asyncio.wait_for(
                    llm_service.generate_summary(
                        raw_text[:3000],  # Use first 3000 chars
                        max_length=100,
                        style="concise"
                    ),
                    timeout=20.0  # 20 second timeout
                )
                job.progress = 90
                await self._notify_job_progress(job)
                logger.info(f"Summary generated for {job.document_id}")
            except asyncio.TimeoutError:
                logger.warning(f"Summary generation timed out for {job.document_id}, using fallback")
                lines = raw_text.split('\n')
                non_empty_lines = [line.strip() for line in lines if line.strip()][:3]
                summary = ' '.join(non_empty_lines)[:100] if non_empty_lines else "Text document"
            except Exception as e:
                logger.warning(f"Summary generation failed for {job.document_id}: {str(e)}, using fallback")
                lines = raw_text.split('\n')
                non_empty_lines = [line.strip() for line in lines if line.strip()][:3]
                summary = ' '.join(non_empty_lines)[:100] if non_empty_lines else "Text document"

            # Update document with processed content
            updates = {
                "metadata": {
                    "summary": summary,
                    "language": language,
                    "processing_stage": ProcessingStage.COMPLETED
                },
                "content": {
                    "formatted_content": formatted_content,
                    "raw_text": raw_text
                }
            }

            await doc_service.update_document(job.document_id, updates, job.user_id)

            # Mark as completed
            job.status = ProcessingStage.COMPLETED
            job.progress = 100
            job.completed_at = datetime.utcnow()

            # Move to completed
            async with self.processing_lock:
                self.completed_jobs[job.job_id] = job
                if job.job_id in self.active_jobs:
                    del self.active_jobs[job.job_id]
                self.current_processing -= 1

            # Notify completion
            await self._notify_job_completed(job)

            # Clean up temp file if it exists
            import os
            if os.path.exists(job.file_path):
                try:
                    os.unlink(job.file_path)
                    logger.info(f"Cleaned up temp file: {job.file_path}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up temp file {job.file_path}: {cleanup_error}")

            logger.info(f"Job {job.job_id} completed successfully")

        except Exception as e:
            logger.error(f"Error processing job {job.job_id}: {e}")

            # Mark as failed
            job.status = ProcessingStage.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()

            # Move to completed
            async with self.processing_lock:
                self.completed_jobs[job.job_id] = job
                if job.job_id in self.active_jobs:
                    del self.active_jobs[job.job_id]
                self.current_processing -= 1

            # Notify failure
            await self._notify_job_failed(job)

            # Clean up temp file even on failure
            import os
            if os.path.exists(job.file_path):
                try:
                    os.unlink(job.file_path)
                    logger.info(f"Cleaned up temp file after failure: {job.file_path}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up temp file {job.file_path}: {cleanup_error}")

    def _update_queue_positions(self):
        """Update queue positions for all pending jobs."""
        position = 1
        for job in self.queue:
            job.queue_position = position
            position += 1

    async def _process_redis_queue(self):
        """Process documents from Redis queue"""
        logger.info("Redis queue processor started")

        while True:
            try:
                # Dequeue documents based on concurrency limit
                documents = await self.redis_queue.dequeue(batch_size=1)

                if not documents:
                    await asyncio.sleep(1)
                    continue

                # Process each document
                for document in documents:
                    asyncio.create_task(self._process_redis_document(document))

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Redis queue processor: {e}")
                await asyncio.sleep(5)

    async def _process_redis_document(self, document: DocumentMessage):
        """Process a document from Redis queue"""
        document_id = document.metadata.document_id
        file_path = document.metadata.file_path

        try:
            logger.info(f"Processing document {document_id} from Redis queue")

            # Import here to avoid circular dependency
            from src.services.service_factory import ServiceFactory, ServiceType
            from src.services.document_service import DocumentService
            from src.models.document import DocumentType
            import aiofiles

            # Get services
            doc_service = DocumentService()
            pdf_service = ServiceFactory.create(ServiceType.PDF)
            llm_service = ServiceFactory.create(ServiceType.LLM)

            # Determine file type
            file_extension = file_path.split('.')[-1].lower()
            doc_type = {
                'pdf': DocumentType.PDF,
                'txt': DocumentType.MARKDOWN,
                'md': DocumentType.MARKDOWN,
                'json': DocumentType.JSON,
                'xml': DocumentType.XML,
                'csv': DocumentType.CSV,
                'xls': DocumentType.EXCEL,
                'xlsx': DocumentType.EXCEL
            }.get(file_extension, DocumentType.MARKDOWN)

            # Process based on file type
            if doc_type == DocumentType.PDF:
                logger.info(f"Processing PDF: {file_path}")
                formatted_content = await pdf_service.pdf_to_markdown(file_path)
                raw_text = formatted_content
            else:
                # Read file content
                logger.info(f"Reading file: {file_path}")
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    raw_text = await f.read()

                # Process with LLM for markdown conversion
                logger.info(f"Converting to markdown using LLM: {file_path}")
                formatted_content = await asyncio.wait_for(
                    llm_service.text_to_markdown(raw_text),
                    timeout=30
                )

            # Generate summary and detect language
            logger.info(f"Generating summary for: {document_id}")
            summary = await asyncio.wait_for(
                llm_service.generate_summary(raw_text[:5000]),
                timeout=20
            )

            logger.info(f"Detecting language for: {document_id}")
            language = await asyncio.wait_for(
                llm_service.detect_language(raw_text[:1000]),
                timeout=10
            )

            # Update document with processed content
            document.content.formatted_content = formatted_content
            document.content.raw_text = raw_text
            document.metadata.summary = summary
            document.metadata.language = language

            # Save updated document
            await doc_service.storage.save(document)

            # Mark as completed in Redis queue
            await self.redis_queue.mark_completed(document_id)

            # Send WebSocket notification
            if self._websocket_service:
                await self._websocket_service.broadcast({
                    "type": "document:processing_complete",
                    "data": {
                        "document_id": document_id,
                        "status": "completed"
                    }
                })

            # Clean up temp file if it exists
            import os
            if os.path.exists(file_path):
                try:
                    os.unlink(file_path)
                    logger.info(f"Cleaned up temp file: {file_path}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up temp file {file_path}: {cleanup_error}")

            logger.info(f"Document {document_id} processed successfully via Redis queue")

        except Exception as e:
            logger.error(f"Error processing document {document_id}: {e}")

            # Mark as failed in Redis queue
            await self.redis_queue.mark_failed(document_id, str(e))

            # Send failure notification
            if self._websocket_service:
                await self._websocket_service.broadcast({
                    "type": "document:processing_failed",
                    "data": {
                        "document_id": document_id,
                        "error": str(e)
                    }
                })

            # Clean up temp file even on failure
            import os
            if file_path and os.path.exists(file_path):
                try:
                    os.unlink(file_path)
                    logger.info(f"Cleaned up temp file after failure: {file_path}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up temp file {file_path}: {cleanup_error}")

    async def _check_stale_jobs(self):
        """Periodically check for stale jobs in Redis queue"""
        while True:
            try:
                await asyncio.sleep(self.settings.queue.stale_job_check_interval)

                if self.redis_queue:
                    recovered = await self.redis_queue.recover_stale_jobs()
                    if recovered > 0:
                        logger.info(f"Recovered {recovered} stale jobs")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error checking stale jobs: {e}")

    async def _persist_job(self, job: ProcessingJob):
        """Persist job to Redis - currently disabled as we store everything in the document."""
        # Jobs are not persisted to Redis separately
        # All job state is maintained in memory and document storage
        pass

    async def _load_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Load job from Redis - currently disabled as we store everything in the document."""
        # Jobs are not loaded from Redis
        # All job state is maintained in memory and document storage
        return None

    # WebSocket notification methods
    async def _notify_job_queued(self, job: ProcessingJob):
        """Notify that a job has been queued."""
        if self._websocket_service:
            await self._websocket_service.broadcast({
                "type": "queue:job_queued",
                "data": job.to_dict()
            })

    async def _notify_job_started(self, job: ProcessingJob):
        """Notify that a job has started processing."""
        if self._websocket_service:
            await self._websocket_service.broadcast({
                "type": "queue:job_started",
                "data": job.to_dict()
            })

    async def _notify_job_progress(self, job: ProcessingJob):
        """Notify job progress update."""
        if self._websocket_service:
            await self._websocket_service.broadcast({
                "type": "queue:job_progress",
                "data": {
                    "job_id": job.job_id,
                    "document_id": job.document_id,
                    "progress": job.progress
                }
            })

    async def _notify_job_completed(self, job: ProcessingJob):
        """Notify that a job has completed."""
        if self._websocket_service:
            await self._websocket_service.broadcast({
                "type": "queue:job_completed",
                "data": job.to_dict()
            })

    async def _notify_job_failed(self, job: ProcessingJob):
        """Notify that a job has failed."""
        if self._websocket_service:
            await self._websocket_service.broadcast({
                "type": "queue:job_failed",
                "data": job.to_dict()
            })

    async def _notify_job_cancelled(self, job: ProcessingJob):
        """Notify that a job has been cancelled."""
        if self._websocket_service:
            await self._websocket_service.broadcast({
                "type": "queue:job_cancelled",
                "data": job.to_dict()
            })

    async def health_check(self) -> Dict[str, Any]:
        """Check health of the queue service."""
        return {
            "service": "QueueService",
            "status": "healthy",
            "queue_length": len(self.queue),
            "processing": self.current_processing,
            "active_jobs": len(self.active_jobs),
            "completed_jobs": len(self.completed_jobs),
            "redis_available": self.use_redis
        }


# Global queue service instance
queue_service = QueueService()