"""Socket.IO server for real-time communication"""
import logging
from typing import Dict, Any
import socketio

logger = logging.getLogger(__name__)

# Create Socket.IO server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=False,
    engineio_logger=False
)

# Create Socket.IO ASGI app
socket_app = socketio.ASGIApp(sio, socketio_path='socket.io')

# Connection tracking
connected_clients: Dict[str, Any] = {}

@sio.event
async def connect(sid, environ, auth):
    """Handle client connection"""
    logger.info(f"Socket.IO client connected: {sid}")
    connected_clients[sid] = {"auth": auth}
    await sio.emit('connected', {'message': 'Connected to server', 'sid': sid}, to=sid)
    return True

@sio.event
async def disconnect(sid):
    """Handle client disconnection"""
    logger.info(f"Socket.IO client disconnected: {sid}")
    if sid in connected_clients:
        del connected_clients[sid]

@sio.event
async def message(sid, data):
    """Handle generic message"""
    logger.info(f"Message from {sid}: {data}")
    await sio.emit('response', {'echo': data}, to=sid)

@sio.event
async def ping(sid, data):
    """Handle ping message"""
    await sio.emit('pong', {'timestamp': data.get('timestamp')}, to=sid)

# Document events
@sio.event
async def document_subscribe(sid, document_id):
    """Subscribe to document updates"""
    logger.info(f"Client {sid} subscribing to document {document_id}")
    await sio.enter_room(sid, f"document:{document_id}")
    await sio.emit('subscribed', {'document_id': document_id}, to=sid)

@sio.event
async def document_unsubscribe(sid, document_id):
    """Unsubscribe from document updates"""
    logger.info(f"Client {sid} unsubscribing from document {document_id}")
    await sio.leave_room(sid, f"document:{document_id}")
    await sio.emit('unsubscribed', {'document_id': document_id}, to=sid)

# Export functions for sending updates
async def emit_document_created(document_data):
    """Emit document created event to all clients"""
    await sio.emit('document:created', document_data)

async def emit_document_updated(document_data):
    """Emit document updated event to all clients"""
    await sio.emit('document:updated', document_data)

async def emit_document_deleted(document_id):
    """Emit document deleted event to all clients"""
    await sio.emit('document:deleted', {'document_id': document_id})

async def emit_processing_progress(job_id, progress):
    """Emit processing progress update"""
    await sio.emit('processing:progress', {'job_id': job_id, 'progress': progress})

# Export the socket app and sio instance
__all__ = ['socket_app', 'sio', 'emit_document_created', 'emit_document_updated',
          'emit_document_deleted', 'emit_processing_progress']