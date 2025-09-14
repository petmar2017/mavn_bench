"""
Queue API Router for document processing queue management.

Provides endpoints for:
- Getting job status
- Getting queue position
- Getting user's jobs
- Cancelling jobs
- Getting overall queue status
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends

from src.api.dependencies import get_current_user
from src.services.queue_service import queue_service
from src.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/queue", tags=["queue"])


@router.get("/job/{job_id}")
async def get_job_status(
    job_id: str,
    user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get the status of a specific processing job.

    Returns job details including status, progress, and queue position.
    """
    job_status = await queue_service.get_job_status(job_id)

    if not job_status:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Check if user owns this job
    if job_status.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    return job_status


@router.get("/job/{job_id}/position")
async def get_queue_position(
    job_id: str,
    user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get the queue position for a specific job.

    Returns the position in the queue (0 if processing or completed).
    """
    position = await queue_service.get_queue_position(job_id)

    if position is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return {"job_id": job_id, "queue_position": position}


@router.get("/user/jobs")
async def get_user_jobs(
    user: dict = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Get all processing jobs for the current user.

    Returns a list of all jobs (pending, processing, completed, failed).
    """
    return await queue_service.get_user_jobs(user["user_id"])


@router.get("/status")
async def get_queue_status() -> Dict[str, Any]:
    """
    Get overall queue status.

    Returns queue statistics including length and processing counts.
    """
    return await queue_service.get_queue_status()


@router.delete("/job/{job_id}")
async def cancel_job(
    job_id: str,
    user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Cancel a pending job.

    Only jobs in pending state can be cancelled.
    """
    # Check if user owns this job
    job_status = await queue_service.get_job_status(job_id)

    if not job_status:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job_status.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    if job_status.get("status") != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job in {job_status.get('status')} state"
        )

    success = await queue_service.cancel_job(job_id)

    if success:
        return {"message": f"Job {job_id} cancelled successfully"}
    else:
        raise HTTPException(status_code=400, detail="Failed to cancel job")


@router.post("/retry/{job_id}")
async def retry_job(
    job_id: str,
    user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Retry a failed job.

    Creates a new job to reprocess the document.
    """
    # Check if user owns this job
    job_status = await queue_service.get_job_status(job_id)

    if not job_status:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job_status.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    if job_status.get("status") != "failed":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot retry job in {job_status.get('status')} state"
        )

    # For now, return a placeholder
    # In real implementation, this would re-enqueue the document
    return {
        "message": "Job retry functionality not yet implemented",
        "original_job_id": job_id
    }