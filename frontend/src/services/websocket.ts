import { io, Socket } from 'socket.io-client';
import { WS_URL } from '../config/api.config';

class WebSocketService {
  private socket: Socket | null = null;
  private listeners: Map<string, Set<(data: any) => void>> = new Map();
  private connectionAttempts: number = 0;
  private debugMode: boolean = true; // Enable debug logging

  private log(level: string, message: string, data?: any) {
    if (this.debugMode) {
      const timestamp = new Date().toISOString();
      const logMessage = `[WebSocket ${timestamp}] ${level}: ${message}`;

      switch (level) {
        case 'DEBUG':
          console.debug(logMessage, data || '');
          break;
        case 'INFO':
          console.log(logMessage, data || '');
          break;
        case 'WARN':
          console.warn(logMessage, data || '');
          break;
        case 'ERROR':
          console.error(logMessage, data || '');
          break;
      }
    }
  }

  connect(apiKey?: string) {
    this.connectionAttempts++;
    const actualApiKey = apiKey || localStorage.getItem('apiKey');

    this.log('INFO', `Connection attempt #${this.connectionAttempts}`, {
      url: WS_URL,
      hasApiKey: !!actualApiKey,
      currentConnection: this.socket?.connected
    });

    if (this.socket?.connected) {
      this.log('DEBUG', 'Already connected, skipping');
      return;
    }

    // Clean up existing socket
    if (this.socket) {
      this.log('DEBUG', 'Cleaning up existing socket');
      this.socket.removeAllListeners();
      this.socket.disconnect();
    }

    this.log('DEBUG', 'Creating new socket connection', {
      url: WS_URL,
      path: '/socket.io',
      transports: ['websocket', 'polling'],
      hasAuth: !!actualApiKey
    });

    this.socket = io(WS_URL, {
      path: '/socket.io',
      transports: ['websocket', 'polling'],
      auth: {
        apiKey: actualApiKey,
      },
      timeout: 20000,
      forceNew: true,
    });

    // Connection event handlers
    this.socket.on('connect', () => {
      this.log('INFO', 'WebSocket connected successfully', {
        id: this.socket?.id,
        transport: this.socket?.io.engine.transport.name,
        url: WS_URL
      });
    });

    this.socket.on('disconnect', (reason) => {
      this.log('WARN', 'WebSocket disconnected', {
        reason,
        id: this.socket?.id,
        wasConnected: this.socket?.connected
      });
    });

    this.socket.on('connect_error', (error) => {
      this.log('ERROR', 'WebSocket connection error', {
        error: error.message,
        type: error.type,
        description: error.description
      });
    });

    this.socket.on('error', (error) => {
      this.log('ERROR', 'WebSocket error', error);
    });

    this.socket.on('reconnect', (attemptNumber) => {
      this.log('INFO', 'WebSocket reconnected', { attemptNumber });
    });

    this.socket.on('reconnect_attempt', (attemptNumber) => {
      this.log('DEBUG', 'WebSocket reconnection attempt', { attemptNumber });
    });

    this.socket.on('reconnect_error', (error) => {
      this.log('ERROR', 'WebSocket reconnection error', error);
    });

    this.socket.on('reconnect_failed', () => {
      this.log('ERROR', 'WebSocket reconnection failed - giving up');
    });

    // Forward all events to registered listeners with logging
    this.socket.onAny((event, ...args) => {
      this.log('DEBUG', `Received event: ${event}`, {
        event,
        argsCount: args.length,
        data: args.length > 0 ? args[0] : undefined
      });

      const listeners = this.listeners.get(event);
      if (listeners && listeners.size > 0) {
        this.log('DEBUG', `Forwarding event to ${listeners.size} listener(s)`, { event });
        listeners.forEach(listener => {
          try {
            listener(...args);
          } catch (error) {
            this.log('ERROR', `Error in event listener for ${event}`, error);
          }
        });
      } else {
        this.log('DEBUG', `No listeners registered for event: ${event}`);
      }
    });

    // Log transport changes
    this.socket.io.on('upgrade', () => {
      this.log('INFO', 'Transport upgraded', {
        transport: this.socket?.io.engine.transport.name
      });
    });

    this.socket.io.on('upgradeError', (error) => {
      this.log('ERROR', 'Transport upgrade error', error);
    });
  }

  disconnect() {
    this.log('INFO', 'Disconnecting WebSocket');
    if (this.socket) {
      this.socket.removeAllListeners();
      this.socket.disconnect();
      this.socket = null;
      this.log('INFO', 'WebSocket disconnected and cleaned up');
    }
  }

  isConnected(): boolean {
    const connected = this.socket?.connected || false;
    this.log('DEBUG', `Connection status check: ${connected}`, {
      socketExists: !!this.socket,
      socketConnected: this.socket?.connected,
      socketId: this.socket?.id
    });
    return connected;
  }

  on(event: string, callback: (data: any) => void) {
    this.log('DEBUG', `Registering listener for event: ${event}`);

    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback);

    const listenerCount = this.listeners.get(event)!.size;
    this.log('DEBUG', `Event listener registered`, {
      event,
      totalListeners: listenerCount,
      allEvents: Array.from(this.listeners.keys())
    });

    // Return unsubscribe function
    return () => {
      this.log('DEBUG', `Unregistering listener for event: ${event}`);
      const listeners = this.listeners.get(event);
      if (listeners) {
        listeners.delete(callback);
        if (listeners.size === 0) {
          this.listeners.delete(event);
          this.log('DEBUG', `All listeners removed for event: ${event}`);
        }
      }
    };
  }

  emit(event: string, data: any) {
    this.log('DEBUG', `Emitting event: ${event}`, {
      event,
      connected: this.socket?.connected,
      data
    });

    if (this.socket?.connected) {
      this.socket.emit(event, data);
      this.log('DEBUG', `Event emitted successfully: ${event}`);
    } else {
      this.log('WARN', `Cannot emit event - WebSocket not connected`, {
        event,
        socketExists: !!this.socket,
        socketConnected: this.socket?.connected
      });
    }
  }

  // Connection status and debugging
  getConnectionInfo() {
    const info = {
      connected: this.socket?.connected || false,
      socketId: this.socket?.id || null,
      transport: this.socket?.io?.engine?.transport?.name || null,
      url: WS_URL,
      connectionAttempts: this.connectionAttempts,
      registeredEvents: Array.from(this.listeners.keys()),
      totalListeners: Array.from(this.listeners.entries()).reduce(
        (total, [, listeners]) => total + listeners.size,
        0
      )
    };

    this.log('INFO', 'Connection info requested', info);
    return info;
  }

  // Document-specific events
  onDocumentCreated(callback: (data: any) => void) {
    this.log('DEBUG', 'Registering document:created listener');
    return this.on('document:created', callback);
  }

  onDocumentUpdated(callback: (data: any) => void) {
    this.log('DEBUG', 'Registering document:updated listener');
    return this.on('document:updated', callback);
  }

  onDocumentDeleted(callback: (data: any) => void) {
    this.log('DEBUG', 'Registering document:deleted listener');
    return this.on('document:deleted', callback);
  }

  onDocumentProcessing(documentId: string, callback: (status: any) => void) {
    const event = `document:processing:${documentId}`;
    this.log('DEBUG', `Registering ${event} listener`);
    return this.on(event, callback);
  }

  onDocumentComplete(documentId: string, callback: (result: any) => void) {
    const event = `document:complete:${documentId}`;
    this.log('DEBUG', `Registering ${event} listener`);
    return this.on(event, callback);
  }

  onDocumentError(documentId: string, callback: (error: any) => void) {
    const event = `document:error:${documentId}`;
    this.log('DEBUG', `Registering ${event} listener`);
    return this.on(event, callback);
  }

  // Processing events
  onProcessingProgress(callback: (progress: any) => void) {
    this.log('DEBUG', 'Registering processing:progress listener');
    return this.on('processing:progress', callback);
  }

  // Search events
  onSearchUpdate(callback: (update: any) => void) {
    this.log('DEBUG', 'Registering search:update listener');
    return this.on('search:update', callback);
  }

  // System events
  onSystemNotification(callback: (notification: any) => void) {
    this.log('DEBUG', 'Registering system:notification listener');
    return this.on('system:notification', callback);
  }

  // Connection testing and debugging
  async testConnection(): Promise<boolean> {
    const testTimestamp = new Date().toISOString();

    this.log('INFO', 'Starting connection test', {
      currentlyConnected: this.isConnected(),
      socketExists: !!this.socket,
      url: WS_URL
    });

    if (!this.isConnected()) {
      this.log('WARN', 'Connection test failed - not connected');
      return false;
    }

    try {
      // Test connection with ping
      return new Promise((resolve) => {
        let resolved = false;
        const timeout = setTimeout(() => {
          if (!resolved) {
            resolved = true;
            this.log('ERROR', 'Connection test failed - ping timeout');
            resolve(false);
          }
        }, 5000);

        // Listen for pong response
        const unsubscribe = this.on('pong', (data) => {
          if (!resolved) {
            resolved = true;
            clearTimeout(timeout);
            this.log('INFO', 'Connection test successful - received pong', data);
            unsubscribe();
            resolve(true);
          }
        });

        // Send ping
        this.log('DEBUG', 'Sending ping for connection test');
        this.emit('ping', { timestamp: testTimestamp, test: true });
      });
    } catch (error) {
      this.log('ERROR', 'Connection test failed with error', error);
      return false;
    }
  }

  // Enable/disable debug mode
  setDebugMode(enabled: boolean) {
    this.debugMode = enabled;
    this.log('INFO', `Debug mode ${enabled ? 'enabled' : 'disabled'}`);
  }

  // Get all registered event listeners
  getRegisteredEvents() {
    return {
      events: Array.from(this.listeners.keys()),
      totalListeners: Array.from(this.listeners.entries()).reduce(
        (total, [, listeners]) => total + listeners.size,
        0
      ),
      listenerDetails: Array.from(this.listeners.entries()).map(([event, listeners]) => ({
        event,
        count: listeners.size
      }))
    };
  }
}

export const wsService = new WebSocketService();