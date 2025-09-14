# WebSocket Debugging Guide

## Logging Enhancements Added

This guide explains the comprehensive logging system added to diagnose WebSocket and document upload issues.

### 1. Frontend WebSocket Service (`frontend/src/services/websocket.ts`)

**Enhanced Features:**
- Detailed connection attempt tracking with retry counts
- Comprehensive event logging with timestamps
- Transport upgrade monitoring
- Connection status validation
- Event listener registration tracking
- Debug mode toggle capability
- Connection testing functionality

**Log Patterns to Look For:**
```
[WebSocket 2024-01-XX] INFO: Connection attempt #1
[WebSocket 2024-01-XX] DEBUG: Creating new socket connection
[WebSocket 2024-01-XX] INFO: WebSocket connected successfully
[WebSocket 2024-01-XX] DEBUG: Received event: system:notification
[WebSocket 2024-01-XX] DEBUG: Forwarding event to 3 listener(s)
```

### 2. Frontend Document Upload (`frontend/src/components/DocumentUpload.tsx`)

**Enhanced Features:**
- File drop event detailed logging
- Upload queue management tracking
- API response validation
- Progress update monitoring
- Success/error state transitions

**Log Patterns to Look For:**
```
[UPLOAD 2024-01-XX] onDrop called
[UPLOAD-PROCESS 2024-01-XX] Starting sequential processing
[UPLOAD-FILE 2024-01-XX] Processing file: example.pdf
[UPLOAD-API 2024-01-XX] Making API call to createDocument
[UPLOAD-API 2024-01-XX] API response received
[UPLOAD-CALLBACK 2024-01-XX] Calling onUploadSuccess callback
```

### 3. Frontend Document List (`frontend/src/components/DocumentList.tsx`)

**Enhanced Features:**
- Document fetch operation tracking
- WebSocket event listener setup monitoring
- API response processing validation
- Real-time update event handling

**Log Patterns to Look For:**
```
[DOCLIST 2024-01-XX] Starting document fetch
[DOCLIST 2024-01-XX] API response received
[DOCLIST-WS 2024-01-XX] Setting up WebSocket listeners
[DOCLIST-WS 2024-01-XX] Document created event received
[DOCLIST-WS 2024-01-XX] Triggering document refresh
```

### 4. Backend Socket.IO Server (`backend/src/api/socketio_app.py`)

**Enhanced Features:**
- Client connection/disconnection detailed tracking
- Event emission comprehensive logging
- Client session information storage
- Broadcast testing capabilities
- Error handling and recovery

**Log Patterns to Look For:**
```
[SOCKETIO 2024-01-XX] CONNECT: {"event": "connect", "sid": "abc123"}
[SOCKETIO-EMIT 2024-01-XX] EMIT_DOCUMENT_CREATED starting
[SOCKETIO-EMIT 2024-01-XX] system:notification emitted
[SOCKETIO-EMIT 2024-01-XX] document:created emitted
[SOCKETIO-EMIT 2024-01-XX] EMIT_DOCUMENT_CREATED completed successfully
```

### 5. Backend Document Router (`backend/src/api/routers/documents.py`)

**Enhanced Features:**
- WebSocket emission trigger logging
- Payload structure validation
- Success/failure tracking for WebSocket events
- Debug endpoint for connection status

**Log Patterns to Look For:**
```
[WEBSOCKET-EMIT] Emitting document_created event for file upload document
[WEBSOCKET-EMIT] Successfully emitted document_created event for doc-123
```

## Debugging Tools Available

### 1. Browser Console Debug Helper

Access via browser console:
```javascript
// Run comprehensive diagnostics
mavnDebug.runDiagnostics()

// Test individual components
mavnDebug.testWebSocket()
mavnDebug.testDocumentApi()

// Enable verbose logging
mavnDebug.enableDebugLogging()

// Monitor events in real-time
const stopMonitoring = mavnDebug.monitorWebSocketEvents()
// stopMonitoring() when done
```

### 2. Backend Debug Endpoint

**GET** `/api/documents/debug/websocket`

Returns:
- Connected client count and details
- Connection information
- Broadcast test results

### 3. WebSocket Connection Testing

Frontend connection test:
```javascript
await wsService.testConnection()
wsService.getConnectionInfo()
wsService.getRegisteredEvents()
```

## Diagnostic Checklist

### 1. Upload File and Check These Logs:

1. **Frontend Upload Logs:**
   - Look for `[UPLOAD` logs showing file processing
   - Check for API call success: `API response received`
   - Verify callback execution: `Calling onUploadSuccess callback`

2. **Backend API Logs:**
   - Look for document creation: `Direct-content document created` or file upload processing
   - Check WebSocket emission: `[WEBSOCKET-EMIT] Emitting document_created event`
   - Verify emission success: `Successfully emitted document_created event`

3. **Backend Socket.IO Logs:**
   - Check event emission: `[SOCKETIO-EMIT] EMIT_DOCUMENT_CREATED starting`
   - Verify broadcast: `system:notification emitted` and `document:created emitted`
   - Confirm completion: `EMIT_DOCUMENT_CREATED completed successfully`

4. **Frontend WebSocket Logs:**
   - Look for event reception: `[WebSocket] DEBUG: Received event: system:notification`
   - Check listener forwarding: `Forwarding event to X listener(s)`
   - Verify document list refresh: `[DOCLIST-WS] Document created event received`

5. **Frontend Document List Logs:**
   - Check refresh trigger: `Triggering document refresh`
   - Verify API call: `Making API call to listDocuments`
   - Confirm update: `Documents processed and sorted`

### 2. Connection Status Verification:

1. **Check WebSocket Connection:**
   ```javascript
   wsService.isConnected()
   wsService.getConnectionInfo()
   ```

2. **Backend Client Count:**
   - Check logs for `connected_clients: X` in WebSocket operations
   - Use debug endpoint: `GET /api/documents/debug/websocket`

3. **Test Broadcast:**
   ```javascript
   mavnDebug.testWebSocket()
   ```

### 3. Common Issues and Their Log Signatures:

**WebSocket Not Connected:**
```
[WebSocket] WARN: Cannot emit event - WebSocket not connected
[DOCLIST-WS] WebSocket not connected
```

**API Errors:**
```
[UPLOAD-ERROR] File upload failed
[DOCLIST] Failed to fetch documents
```

**Event Not Received:**
```
[WebSocket] DEBUG: No listeners registered for event: system:notification
[DOCLIST-WS] Notification ignored - not document related
```

**Backend Emission Failures:**
```
[WEBSOCKET-EMIT] Failed to emit document created event
[SOCKETIO-EMIT] EMIT_DOCUMENT_CREATED failed
```

## Quick Start Debugging

1. **Open browser console and run:**
   ```javascript
   mavnDebug.enableDebugLogging()
   mavnDebug.runDiagnostics()
   ```

2. **Upload a test file and watch console logs**

3. **Check these key indicators:**
   - WebSocket connection status: ✅/❌
   - API test result: ✅/❌
   - Document upload logs
   - Event emission logs
   - Event reception logs
   - Document list refresh logs

4. **If issues found, check backend logs for:**
   - Socket.IO client connections
   - Document creation events
   - WebSocket emission attempts

This comprehensive logging system should help identify exactly where the document upload → WebSocket event → document list refresh chain is breaking.