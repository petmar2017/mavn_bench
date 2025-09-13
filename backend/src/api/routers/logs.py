"""
Client-side logging endpoint for centralized error tracking and monitoring.
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime
import logging
import json
from ...core.logger import CentralizedLogger

# Get logger for this module
logger = CentralizedLogger(__name__)

# Create a separate logger for client logs
client_logger = CentralizedLogger("client")

router = APIRouter(prefix="/api", tags=["logging"])


class ClientLogEntry(BaseModel):
    """Individual log entry from client."""
    level: str = Field(..., description="Log level: debug, info, warn, error")
    message: str = Field(..., description="Log message")
    timestamp: str = Field(..., description="ISO timestamp when log was created")
    context: Optional[Any] = Field(None, description="Additional context data")
    stackTrace: Optional[str] = Field(None, description="Stack trace for errors")
    userAgent: Optional[str] = Field(None, description="Browser user agent")
    url: Optional[str] = Field(None, description="Page URL where log was generated")


class ClientLogBatch(BaseModel):
    """Batch of logs from client."""
    logs: List[ClientLogEntry] = Field(..., description="Array of log entries")
    sessionId: str = Field(..., description="Client session identifier")
    timestamp: str = Field(..., description="ISO timestamp when batch was sent")


@router.post("/client-logs", status_code=202)
async def receive_client_logs(
    batch: ClientLogBatch,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Receive and process client-side logs.

    Logs are processed asynchronously to avoid blocking the response.
    Returns immediately with accepted status.
    """
    try:
        # Validate batch size
        if len(batch.logs) > 100:
            raise HTTPException(
                status_code=400,
                detail="Batch size too large. Maximum 100 logs per batch."
            )

        # Process logs in background
        background_tasks.add_task(process_client_logs, batch)

        logger.debug(f"Accepted {len(batch.logs)} logs from session {batch.sessionId}")

        return {
            "status": "accepted",
            "count": len(batch.logs),
            "sessionId": batch.sessionId
        }

    except Exception as e:
        logger.error(f"Error receiving client logs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process logs")


def process_client_logs(batch: ClientLogBatch):
    """
    Process client logs asynchronously.

    Logs are formatted and sent to appropriate log levels.
    Critical errors are highlighted for monitoring.
    """
    session_id = batch.sessionId

    for log_entry in batch.logs:
        try:
            # Build formatted message
            message_parts = [
                f"[SESSION:{session_id}]",
                log_entry.message
            ]

            # Add URL if available
            if log_entry.url:
                message_parts.append(f"| URL: {log_entry.url}")

            # Add user agent for first error in session
            if log_entry.userAgent and log_entry.level == "error":
                message_parts.append(f"| UA: {log_entry.userAgent[:100]}")

            message = " ".join(message_parts)

            # Add context as structured data
            extra_data = {
                "session_id": session_id,
                "client_timestamp": log_entry.timestamp,
                "url": log_entry.url,
            }

            # Add context if present
            if log_entry.context:
                extra_data["context"] = log_entry.context
                # For errors, include context in message
                if log_entry.level == "error":
                    try:
                        context_str = json.dumps(log_entry.context, indent=2)
                        message += f"\nContext:\n{context_str}"
                    except:
                        message += f"\nContext: {str(log_entry.context)}"

            # Add stack trace for errors
            if log_entry.stackTrace and log_entry.level == "error":
                message += f"\n\nStack Trace:\n{log_entry.stackTrace}"

            # Log at appropriate level
            if log_entry.level == "error":
                client_logger.error(message, extra=extra_data)

                # Also log critical errors to main logger
                if "unhandled" in log_entry.message.lower():
                    logger.error(f"Critical client error: {message}")

            elif log_entry.level == "warn":
                client_logger.warning(message, extra=extra_data)

            elif log_entry.level == "info":
                client_logger.info(message, extra=extra_data)

            else:  # debug
                client_logger.debug(message, extra=extra_data)

        except Exception as e:
            # Don't let a single bad log entry break the whole batch
            logger.error(f"Error processing client log entry: {str(e)}")
            continue


@router.get("/client-logs/health")
async def client_logging_health() -> Dict[str, str]:
    """
    Health check endpoint for client logging service.
    """
    return {
        "status": "healthy",
        "service": "client-logging",
        "timestamp": datetime.utcnow().isoformat()
    }