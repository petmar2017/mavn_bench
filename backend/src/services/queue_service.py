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
from src.models.document import ProcessingStage, DocumentType
from src.core.logger import get_logger
from src.storage.storage_factory import StorageFactory, StorageType

logger = get_logger(__name__)


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
        self.queue: deque[ProcessingJob] = deque()
        self.active_jobs: Dict[str, ProcessingJob] = {}
        self.completed_jobs: Dict[str, ProcessingJob] = {}
        self.job_by_document: Dict[str, ProcessingJob] = {}
        self.processing_lock = asyncio.Lock()
        self.max_concurrent_jobs = 3
        self.current_processing = 0
        self._processing_task: Optional[asyncio.Task] = None
        self._websocket_service = None  # Will be injected

        # Use Redis storage if available for queue persistence
        try:
            self.storage = StorageFactory.create(StorageType.REDIS)
            self.use_redis = True
            logger.info("QueueService using Redis for persistence")
        except Exception as e:
            logger.warning(f"Redis not available, using in-memory queue: {e}")
            self.storage = None
            self.use_redis = False

    def set_websocket_service(self, websocket_service):
        """Inject WebSocket service for real-time updates."""
        self._websocket_service = websocket_service

    async def start_processing(self):
        """Start the background processing task."""
        if not self._processing_task or self._processing_task.done():
            self._processing_task = asyncio.create_task(self._process_queue())
            logger.info("Queue processing started")

    async def stop_processing(self):
        """Stop the background processing task."""
        if self._processing_task and not self._processing_task.done():
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
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

                # Persist to Redis if available
                if self.use_redis:
                    await self._persist_job(job)

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
        return {
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

                # Validate and potentially re-extract with LLM if quality is poor
                validation_result = await pdf_service.validate_and_extract_pdf(
                    job.file_path,
                    markdown_content
                )
                job.progress = 50
                await self._notify_job_progress(job)

                if validation_result.get("needs_reprocessing"):
                    logger.info(f"PDF extraction was poor quality, using LLM-improved version")
                    formatted_content = validation_result["improved_extraction"]
                    raw_text = validation_result["improved_extraction"]
                else:
                    formatted_content = markdown_content
                    raw_text = markdown_content

            elif job.file_type in [DocumentType.WORD.value, DocumentType.TEXT.value]:
                # For Word and text files, extract text and convert to markdown
                async with aiofiles.open(job.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    raw_text = await f.read()

                job.progress = 30
                await self._notify_job_progress(job)

                # Use LLM to format as markdown
                try:
                    formatted_content = await llm_service.text_to_markdown(raw_text[:10000])  # Limit input
                except:
                    formatted_content = raw_text  # Fallback to raw text

                job.progress = 50
                await self._notify_job_progress(job)
            else:
                # For other types, read as text
                async with aiofiles.open(job.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    raw_text = await f.read()
                formatted_content = raw_text
                job.progress = 50
                await self._notify_job_progress(job)

            # Detect language and generate summary
            language = "en"  # Default
            summary = None
            try:
                # Detect language
                lang_result = await llm_service.detect_language(raw_text[:1000])
                language = lang_result[0] if lang_result and lang_result[0] != "unknown" else "en"
                job.progress = 70
                await self._notify_job_progress(job)

                # Generate summary
                summary = await llm_service.generate_summary(
                    raw_text[:3000],  # Use first 3000 chars
                    max_length=100,
                    style="concise"
                )
                job.progress = 90
                await self._notify_job_progress(job)
            except Exception as e:
                logger.warning(f"Failed to detect language or generate summary: {str(e)}")
                summary = "Processing completed"

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

    def _update_queue_positions(self):
        """Update queue positions for all pending jobs."""
        position = 1
        for job in self.queue:
            job.queue_position = position
            position += 1

    async def _persist_job(self, job: ProcessingJob):
        """Persist job to Redis."""
        if self.storage:
            try:
                key = f"queue:job:{job.job_id}"
                await self.storage.save(key, job.to_dict())
            except Exception as e:
                logger.error(f"Failed to persist job to Redis: {e}")

    async def _load_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Load job from Redis."""
        if self.storage:
            try:
                key = f"queue:job:{job_id}"
                return await self.storage.load(key)
            except Exception as e:
                logger.error(f"Failed to load job from Redis: {e}")
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