"""WebSocket endpoints for real-time document processing"""

import json
from typing import Dict, Set, Any, Optional
from datetime import datetime
import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from opentelemetry import trace

from ...core.logger import CentralizedLogger
from ...core.config import get_settings
from ..dependencies import verify_api_key_ws


router = APIRouter()
logger = CentralizedLogger("WebSocketRouter")
tracer = trace.get_tracer(__name__)
settings = get_settings()


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting"""

    def __init__(self):
        """Initialize connection manager"""
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, Set[str]] = {}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        connection_id: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Accept and track new WebSocket connection

        Args:
            websocket: WebSocket connection
            connection_id: Unique connection ID
            user_id: User ID
            metadata: Optional connection metadata
        """
        await websocket.accept()
        self.active_connections[connection_id] = websocket

        # Track user connections
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)

        # Store metadata
        self.connection_metadata[connection_id] = {
            "user_id": user_id,
            "connected_at": datetime.utcnow().isoformat(),
            **(metadata or {})
        }

        logger.info(f"WebSocket connected: {connection_id} for user {user_id}")

    def disconnect(self, connection_id: str):
        """Remove WebSocket connection

        Args:
            connection_id: Connection ID to remove
        """
        if connection_id in self.active_connections:
            # Get user ID
            metadata = self.connection_metadata.get(connection_id, {})
            user_id = metadata.get("user_id")

            # Remove from active connections
            del self.active_connections[connection_id]

            # Remove from user connections
            if user_id and user_id in self.user_connections:
                self.user_connections[user_id].discard(connection_id)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]

            # Remove metadata
            if connection_id in self.connection_metadata:
                del self.connection_metadata[connection_id]

            logger.info(f"WebSocket disconnected: {connection_id}")

    async def send_personal_message(
        self,
        message: Dict[str, Any],
        connection_id: str
    ):
        """Send message to specific connection

        Args:
            message: Message to send
            connection_id: Target connection ID
        """
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message to {connection_id}: {str(e)}")
                self.disconnect(connection_id)

    async def send_user_message(
        self,
        message: Dict[str, Any],
        user_id: str
    ):
        """Send message to all connections for a user

        Args:
            message: Message to send
            user_id: Target user ID
        """
        if user_id in self.user_connections:
            for connection_id in list(self.user_connections[user_id]):
                await self.send_personal_message(message, connection_id)

    async def broadcast(
        self,
        message: Dict[str, Any],
        exclude_connection: Optional[str] = None
    ):
        """Broadcast message to all connected clients

        Args:
            message: Message to broadcast
            exclude_connection: Optional connection to exclude
        """
        disconnected = []
        for connection_id, websocket in list(self.active_connections.items()):
            if connection_id != exclude_connection:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to broadcast to {connection_id}: {str(e)}")
                    disconnected.append(connection_id)

        # Clean up disconnected clients
        for connection_id in disconnected:
            self.disconnect(connection_id)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Simple WebSocket endpoint for Socket.IO compatibility"""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")


@router.websocket("/ws/documents")
async def websocket_documents(
    websocket: WebSocket,
    api_key: Optional[str] = Query(None),
    connection_id: Optional[str] = Query(None)
):
    """WebSocket endpoint for document updates

    Args:
        websocket: WebSocket connection
        api_key: API key for authentication
        connection_id: Optional client-provided connection ID
    """
    # Validate API key
    user = await verify_api_key_ws(api_key)
    if not user:
        await websocket.close(code=1008, reason="Unauthorized")
        return

    # Generate connection ID if not provided
    if not connection_id:
        connection_id = f"ws_{datetime.utcnow().timestamp()}"

    # Create span for connection
    with tracer.start_as_current_span("websocket_documents") as span:
        span.set_attribute("connection.id", connection_id)
        span.set_attribute("user.id", user["user_id"])

        # Connect client
        await manager.connect(
            websocket,
            connection_id,
            user["user_id"],
            metadata={"endpoint": "documents"}
        )

        # Send welcome message
        await manager.send_personal_message(
            {
                "type": "connection",
                "status": "connected",
                "connection_id": connection_id,
                "timestamp": datetime.utcnow().isoformat()
            },
            connection_id
        )

        try:
            while True:
                # Receive message from client
                data = await websocket.receive_json()

                # Process message based on type
                message_type = data.get("type")

                if message_type == "ping":
                    # Respond to ping
                    await manager.send_personal_message(
                        {
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat()
                        },
                        connection_id
                    )

                elif message_type == "subscribe":
                    # Subscribe to document updates
                    document_id = data.get("document_id")
                    if document_id:
                        # Store subscription in metadata
                        manager.connection_metadata[connection_id]["subscriptions"] = \
                            manager.connection_metadata[connection_id].get("subscriptions", set())
                        manager.connection_metadata[connection_id]["subscriptions"].add(document_id)

                        await manager.send_personal_message(
                            {
                                "type": "subscribed",
                                "document_id": document_id,
                                "timestamp": datetime.utcnow().isoformat()
                            },
                            connection_id
                        )

                elif message_type == "unsubscribe":
                    # Unsubscribe from document updates
                    document_id = data.get("document_id")
                    if document_id:
                        subscriptions = manager.connection_metadata[connection_id].get("subscriptions", set())
                        subscriptions.discard(document_id)

                        await manager.send_personal_message(
                            {
                                "type": "unsubscribed",
                                "document_id": document_id,
                                "timestamp": datetime.utcnow().isoformat()
                            },
                            connection_id
                        )

                else:
                    # Unknown message type
                    await manager.send_personal_message(
                        {
                            "type": "error",
                            "message": f"Unknown message type: {message_type}",
                            "timestamp": datetime.utcnow().isoformat()
                        },
                        connection_id
                    )

        except WebSocketDisconnect:
            manager.disconnect(connection_id)
            logger.info(f"Client {connection_id} disconnected normally")

        except Exception as e:
            logger.error(f"WebSocket error for {connection_id}: {str(e)}")
            manager.disconnect(connection_id)
            span.record_exception(e)


@router.websocket("/ws/processing")
async def websocket_processing(
    websocket: WebSocket,
    api_key: Optional[str] = Query(None),
    connection_id: Optional[str] = Query(None)
):
    """WebSocket endpoint for processing status updates

    Args:
        websocket: WebSocket connection
        api_key: API key for authentication
        connection_id: Optional client-provided connection ID
    """
    # Validate API key
    user = await verify_api_key_ws(api_key)
    if not user:
        await websocket.close(code=1008, reason="Unauthorized")
        return

    # Generate connection ID if not provided
    if not connection_id:
        connection_id = f"ws_{datetime.utcnow().timestamp()}"

    # Create span for connection
    with tracer.start_as_current_span("websocket_processing") as span:
        span.set_attribute("connection.id", connection_id)
        span.set_attribute("user.id", user["user_id"])

        # Connect client
        await manager.connect(
            websocket,
            connection_id,
            user["user_id"],
            metadata={"endpoint": "processing"}
        )

        # Send welcome message
        await manager.send_personal_message(
            {
                "type": "connection",
                "status": "connected",
                "connection_id": connection_id,
                "timestamp": datetime.utcnow().isoformat()
            },
            connection_id
        )

        try:
            while True:
                # Receive message from client
                data = await websocket.receive_json()

                # Process message based on type
                message_type = data.get("type")

                if message_type == "ping":
                    # Respond to ping
                    await manager.send_personal_message(
                        {
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat()
                        },
                        connection_id
                    )

                elif message_type == "status":
                    # Request processing status
                    job_id = data.get("job_id")
                    if job_id:
                        # Would query actual job status
                        await manager.send_personal_message(
                            {
                                "type": "status_update",
                                "job_id": job_id,
                                "status": "processing",  # Would be actual status
                                "progress": 45,  # Would be actual progress
                                "timestamp": datetime.utcnow().isoformat()
                            },
                            connection_id
                        )

                elif message_type == "cancel":
                    # Cancel processing job
                    job_id = data.get("job_id")
                    if job_id:
                        # Would cancel actual job
                        await manager.send_personal_message(
                            {
                                "type": "cancelled",
                                "job_id": job_id,
                                "timestamp": datetime.utcnow().isoformat()
                            },
                            connection_id
                        )

                else:
                    # Unknown message type
                    await manager.send_personal_message(
                        {
                            "type": "error",
                            "message": f"Unknown message type: {message_type}",
                            "timestamp": datetime.utcnow().isoformat()
                        },
                        connection_id
                    )

        except WebSocketDisconnect:
            manager.disconnect(connection_id)
            logger.info(f"Client {connection_id} disconnected normally")

        except Exception as e:
            logger.error(f"WebSocket error for {connection_id}: {str(e)}")
            manager.disconnect(connection_id)
            span.record_exception(e)


async def send_document_update(
    document_id: str,
    update_type: str,
    data: Dict[str, Any]
):
    """Send document update to subscribed clients

    Args:
        document_id: Document ID
        update_type: Type of update (created, updated, deleted)
        data: Update data
    """
    message = {
        "type": "document_update",
        "document_id": document_id,
        "update_type": update_type,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }

    # Send to all connections subscribed to this document
    for connection_id, metadata in manager.connection_metadata.items():
        subscriptions = metadata.get("subscriptions", set())
        if document_id in subscriptions:
            await manager.send_personal_message(message, connection_id)


async def send_processing_update(
    user_id: str,
    job_id: str,
    status: str,
    progress: Optional[int] = None,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None
):
    """Send processing update to user

    Args:
        user_id: User ID
        job_id: Processing job ID
        status: Job status (queued, processing, completed, failed)
        progress: Optional progress percentage
        result: Optional result data
        error: Optional error message
    """
    message = {
        "type": "processing_update",
        "job_id": job_id,
        "status": status,
        "timestamp": datetime.utcnow().isoformat()
    }

    if progress is not None:
        message["progress"] = progress
    if result is not None:
        message["result"] = result
    if error is not None:
        message["error"] = error

    # Send to all connections for this user
    await manager.send_user_message(message, user_id)


@router.get("/ws/connections")
async def get_connections(
    user: Dict = Depends(verify_api_key_ws)
) -> Dict[str, Any]:
    """Get current WebSocket connections (admin only)

    Args:
        user: Current user

    Returns:
        Connection statistics

    Raises:
        HTTPException: If not authorized
    """
    # Check admin role
    if "admin" not in user.get("roles", []):
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return {
        "total_connections": len(manager.active_connections),
        "unique_users": len(manager.user_connections),
        "connections_by_user": {
            user_id: len(connections)
            for user_id, connections in manager.user_connections.items()
        },
        "endpoints": {
            "documents": sum(
                1 for m in manager.connection_metadata.values()
                if m.get("endpoint") == "documents"
            ),
            "processing": sum(
                1 for m in manager.connection_metadata.values()
                if m.get("endpoint") == "processing"
            )
        }
    }