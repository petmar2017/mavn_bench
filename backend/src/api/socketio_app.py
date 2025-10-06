"""Socket.IO server for real-time communication"""
import logging
from typing import Dict, Any
import socketio
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# Create Socket.IO server with production logging
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=False,  # Disable Socket.IO internal debug logging
    engineio_logger=False  # Disable EngineIO internal debug logging
)

# Create Socket.IO ASGI app
socket_app = socketio.ASGIApp(sio, socketio_path='socket.io')

# Connection tracking
connected_clients: Dict[str, Any] = {}

def log_socketio_event(event_name: str, sid: str, data: Any = None):
    """Helper function to log Socket.IO events with consistent formatting"""
    timestamp = datetime.now().isoformat()
    client_count = len(connected_clients)

    log_data = {
        'event': event_name,
        'sid': sid,
        'timestamp': timestamp,
        'client_count': client_count,
        'data': data
    }

    logger.info(f"[SOCKETIO {timestamp}] {event_name.upper()}: {json.dumps(log_data, default=str)}")

@sio.event
async def connect(sid, environ, auth):
    """Handle client connection"""
    client_info = {
        'sid': sid,
        'auth': auth,
        'user_agent': environ.get('HTTP_USER_AGENT'),
        'remote_addr': environ.get('REMOTE_ADDR'),
        'query_params': environ.get('QUERY_STRING'),
        'headers': {key: value for key, value in environ.items() if key.startswith('HTTP_')},
        'connected_at': datetime.now().isoformat()
    }

    connected_clients[sid] = client_info

    log_socketio_event('connect', sid, {
        'auth_provided': bool(auth),
        'auth_keys': list(auth.keys()) if auth else None,
        'user_agent': environ.get('HTTP_USER_AGENT'),
        'remote_addr': environ.get('REMOTE_ADDR'),
        'total_clients': len(connected_clients)
    })

    # Send connection confirmation
    connection_response = {'message': 'Connected to server', 'sid': sid, 'timestamp': datetime.now().isoformat()}
    await sio.emit('connected', connection_response, to=sid)

    logger.info(f"[SOCKETIO] Connection response sent to {sid}: {connection_response}")
    return True

@sio.event
async def disconnect(sid):
    """Handle client disconnection"""
    client_info = connected_clients.get(sid, {})

    log_socketio_event('disconnect', sid, {
        'was_authenticated': bool(client_info.get('auth')),
        'connected_at': client_info.get('connected_at'),
        'session_duration': (datetime.now() - datetime.fromisoformat(client_info.get('connected_at', datetime.now().isoformat()))).total_seconds() if client_info.get('connected_at') else None,
        'remaining_clients': len(connected_clients) - 1
    })

    if sid in connected_clients:
        del connected_clients[sid]

@sio.event
async def message(sid, data):
    """Handle generic message"""
    log_socketio_event('message', sid, data)
    response = {'echo': data}
    await sio.emit('response', response, to=sid)
    logger.info(f"[SOCKETIO] Response sent to {sid}: {response}")

@sio.event
async def ping(sid, data):
    """Handle ping message"""
    log_socketio_event('ping', sid, data)
    response = {'timestamp': data.get('timestamp'), 'server_time': datetime.now().isoformat()}
    await sio.emit('pong', response, to=sid)
    logger.info(f"[SOCKETIO] Pong sent to {sid}: {response}")

# Document events
@sio.event
async def document_subscribe(sid, document_id):
    """Subscribe to document updates"""
    log_socketio_event('document_subscribe', sid, {'document_id': document_id})

    room_name = f"document:{document_id}"
    await sio.enter_room(sid, room_name)

    response = {'document_id': document_id, 'room': room_name}
    await sio.emit('subscribed', response, to=sid)

    logger.info(f"[SOCKETIO] Client {sid} subscribed to {room_name}, response: {response}")

@sio.event
async def document_unsubscribe(sid, document_id):
    """Unsubscribe from document updates"""
    log_socketio_event('document_unsubscribe', sid, {'document_id': document_id})

    room_name = f"document:{document_id}"
    await sio.leave_room(sid, room_name)

    response = {'document_id': document_id, 'room': room_name}
    await sio.emit('unsubscribed', response, to=sid)

    logger.info(f"[SOCKETIO] Client {sid} unsubscribed from {room_name}, response: {response}")

# Export functions for sending updates
async def emit_document_created(document_data):
    """Emit document created event to all clients"""
    timestamp = datetime.now().isoformat()
    document_id = document_data.get('document_id') or document_data.get('id')
    document_name = document_data.get('name', 'Unknown')

    logger.info(f"[SOCKETIO-EMIT {timestamp}] EMIT_DOCUMENT_CREATED starting", extra={
        'document_id': document_id,
        'document_name': document_name,
        'connected_clients': len(connected_clients),
        'document_data_keys': list(document_data.keys()) if document_data else None
    })

    # Create the notification payload
    system_notification = {
        'type': 'document_created',
        'document_id': document_id,
        'message': f"Document '{document_name}' has been created",
        'data': document_data,
        'timestamp': timestamp
    }

    # Also emit document:created event
    document_event = {
        'id': document_id,
        'name': document_name,
        'data': document_data,
        'timestamp': timestamp
    }

    try:
        # Emit system notification
        await sio.emit('system:notification', system_notification)
        logger.info(f"[SOCKETIO-EMIT {timestamp}] system:notification emitted", extra={
            'event': 'system:notification',
            'payload': system_notification,
            'clients_count': len(connected_clients)
        })

        # Also emit specific document event
        await sio.emit('document:created', document_event)
        logger.info(f"[SOCKETIO-EMIT {timestamp}] document:created emitted", extra={
            'event': 'document:created',
            'payload': document_event,
            'clients_count': len(connected_clients)
        })

        logger.info(f"[SOCKETIO-EMIT {timestamp}] EMIT_DOCUMENT_CREATED completed successfully", extra={
            'document_id': document_id,
            'total_events_sent': 2,
            'clients_notified': len(connected_clients)
        })

    except Exception as e:
        logger.error(f"[SOCKETIO-EMIT {timestamp}] EMIT_DOCUMENT_CREATED failed", extra={
            'error': str(e),
            'error_type': type(e).__name__,
            'document_id': document_id
        })
        raise

async def emit_document_updated(document_data):
    """Emit document updated event to all clients"""
    timestamp = datetime.now().isoformat()
    document_id = document_data.get('document_id') or document_data.get('id')
    document_name = document_data.get('name', 'Unknown')

    logger.info(f"[SOCKETIO-EMIT {timestamp}] EMIT_DOCUMENT_UPDATED starting", extra={
        'document_id': document_id,
        'document_name': document_name,
        'connected_clients': len(connected_clients)
    })

    # Create the notification payload
    system_notification = {
        'type': 'document_updated',
        'document_id': document_id,
        'message': f"Document '{document_name}' has been updated",
        'data': document_data,
        'timestamp': timestamp
    }

    # Also emit document:updated event
    document_event = {
        'id': document_id,
        'name': document_name,
        'data': document_data,
        'timestamp': timestamp
    }

    try:
        # Emit system notification
        await sio.emit('system:notification', system_notification)
        logger.info(f"[SOCKETIO-EMIT {timestamp}] system:notification emitted for update", extra={
            'event': 'system:notification',
            'payload': system_notification
        })

        # Also emit specific document event
        await sio.emit('document:updated', document_event)
        logger.info(f"[SOCKETIO-EMIT {timestamp}] document:updated emitted", extra={
            'event': 'document:updated',
            'payload': document_event
        })

        logger.info(f"[SOCKETIO-EMIT {timestamp}] EMIT_DOCUMENT_UPDATED completed successfully")

    except Exception as e:
        logger.error(f"[SOCKETIO-EMIT {timestamp}] EMIT_DOCUMENT_UPDATED failed", extra={
            'error': str(e),
            'document_id': document_id
        })
        raise

async def emit_document_deleted(document_id):
    """Emit document deleted event to all clients"""
    timestamp = datetime.now().isoformat()

    logger.info(f"[SOCKETIO-EMIT {timestamp}] EMIT_DOCUMENT_DELETED starting", extra={
        'document_id': document_id,
        'connected_clients': len(connected_clients)
    })

    payload = {'document_id': document_id, 'timestamp': timestamp}

    try:
        await sio.emit('document:deleted', payload)
        logger.info(f"[SOCKETIO-EMIT {timestamp}] document:deleted emitted", extra={
            'event': 'document:deleted',
            'payload': payload
        })
    except Exception as e:
        logger.error(f"[SOCKETIO-EMIT {timestamp}] EMIT_DOCUMENT_DELETED failed", extra={
            'error': str(e),
            'document_id': document_id
        })
        raise

async def emit_processing_progress(job_id, progress):
    """Emit processing progress update"""
    timestamp = datetime.now().isoformat()

    logger.info(f"[SOCKETIO-EMIT {timestamp}] EMIT_PROCESSING_PROGRESS", extra={
        'job_id': job_id,
        'progress': progress,
        'connected_clients': len(connected_clients)
    })

    payload = {'job_id': job_id, 'progress': progress, 'timestamp': timestamp}

    try:
        await sio.emit('processing:progress', payload)
        logger.info(f"[SOCKETIO-EMIT {timestamp}] processing:progress emitted")
    except Exception as e:
        logger.error(f"[SOCKETIO-EMIT {timestamp}] EMIT_PROCESSING_PROGRESS failed", extra={
            'error': str(e),
            'job_id': job_id
        })
        raise

# Connection status helpers
def get_connected_clients_count() -> int:
    """Get the number of connected clients"""
    return len(connected_clients)

def get_connected_clients_info() -> Dict[str, Any]:
    """Get detailed information about connected clients"""
    timestamp = datetime.now().isoformat()
    clients_info = []

    for sid, client_data in connected_clients.items():
        client_info = {
            'sid': sid,
            'connected_at': client_data.get('connected_at'),
            'has_auth': bool(client_data.get('auth')),
            'user_agent': client_data.get('user_agent', 'Unknown')[:100],  # Truncate for readability
            'remote_addr': client_data.get('remote_addr', 'Unknown')
        }
        clients_info.append(client_info)

    return {
        'timestamp': timestamp,
        'total_clients': len(connected_clients),
        'clients': clients_info
    }

async def test_emit_to_all() -> Dict[str, Any]:
    """Test function to emit a test event to all connected clients"""
    timestamp = datetime.now().isoformat()
    client_count = len(connected_clients)

    logger.info(f"[SOCKETIO-TEST {timestamp}] Testing broadcast to {client_count} clients")

    test_payload = {
        'type': 'test',
        'message': 'Test broadcast from server',
        'timestamp': timestamp,
        'client_count': client_count
    }

    try:
        await sio.emit('system:notification', test_payload)
        logger.info(f"[SOCKETIO-TEST {timestamp}] Test broadcast sent successfully")
        return {
            'success': True,
            'clients_notified': client_count,
            'payload': test_payload
        }
    except Exception as e:
        logger.error(f"[SOCKETIO-TEST {timestamp}] Test broadcast failed", extra={'error': str(e)})
        return {
            'success': False,
            'error': str(e),
            'clients_notified': 0
        }

# Add error handler for Socket.IO
@sio.event
async def connect_error(sid, data):
    """Handle connection errors"""
    log_socketio_event('connect_error', sid, data)

# Export the socket app and sio instance
__all__ = ['socket_app', 'sio', 'emit_document_created', 'emit_document_updated',
          'emit_document_deleted', 'emit_processing_progress', 'get_connected_clients_count',
          'get_connected_clients_info', 'test_emit_to_all']