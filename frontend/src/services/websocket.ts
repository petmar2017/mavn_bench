import { io, Socket } from 'socket.io-client';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

class WebSocketService {
  private socket: Socket | null = null;
  private listeners: Map<string, Set<(data: any) => void>> = new Map();

  connect(apiKey?: string) {
    if (this.socket?.connected) {
      return;
    }

    this.socket = io(WS_URL, {
      path: '/socket.io',
      transports: ['websocket', 'polling'],
      auth: {
        apiKey: apiKey || localStorage.getItem('apiKey'),
      },
    });

    this.socket.on('connect', () => {
      console.log('WebSocket connected');
    });

    this.socket.on('disconnect', () => {
      console.log('WebSocket disconnected');
    });

    this.socket.on('error', (error) => {
      console.error('WebSocket error:', error);
    });

    // Forward all events to registered listeners
    this.socket.onAny((event, ...args) => {
      const listeners = this.listeners.get(event);
      if (listeners) {
        listeners.forEach(listener => listener(...args));
      }
    });
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  isConnected(): boolean {
    return this.socket?.connected || false;
  }

  on(event: string, callback: (data: any) => void) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(callback);

    // Return unsubscribe function
    return () => {
      const listeners = this.listeners.get(event);
      if (listeners) {
        listeners.delete(callback);
        if (listeners.size === 0) {
          this.listeners.delete(event);
        }
      }
    };
  }

  emit(event: string, data: any) {
    if (this.socket?.connected) {
      this.socket.emit(event, data);
    } else {
      console.warn('WebSocket not connected');
    }
  }

  // Document-specific events
  onDocumentCreated(callback: (data: any) => void) {
    return this.on('document:created', callback);
  }

  onDocumentUpdated(callback: (data: any) => void) {
    return this.on('document:updated', callback);
  }

  onDocumentDeleted(callback: (data: any) => void) {
    return this.on('document:deleted', callback);
  }

  onDocumentProcessing(documentId: string, callback: (status: any) => void) {
    return this.on(`document:processing:${documentId}`, callback);
  }

  onDocumentComplete(documentId: string, callback: (result: any) => void) {
    return this.on(`document:complete:${documentId}`, callback);
  }

  onDocumentError(documentId: string, callback: (error: any) => void) {
    return this.on(`document:error:${documentId}`, callback);
  }

  // Processing events
  onProcessingProgress(callback: (progress: any) => void) {
    return this.on('processing:progress', callback);
  }

  // Search events
  onSearchUpdate(callback: (update: any) => void) {
    return this.on('search:update', callback);
  }

  // System events
  onSystemNotification(callback: (notification: any) => void) {
    return this.on('system:notification', callback);
  }
}

export const wsService = new WebSocketService();