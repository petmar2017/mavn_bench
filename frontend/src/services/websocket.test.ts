import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { io, Socket } from 'socket.io-client';
import { wsService } from './websocket';
import { mockDocument, mockWebSocketEvents } from '../test/mocks';

// Mock socket.io-client
vi.mock('socket.io-client');

describe('WebSocketService', () => {
  let mockSocket: any;

  beforeEach(() => {
    // Create a mock socket
    mockSocket = {
      connected: false,
      on: vi.fn(),
      off: vi.fn(),
      emit: vi.fn(),
      disconnect: vi.fn(),
      connect: vi.fn(),
      onAny: vi.fn(),
    };

    // Mock io to return our mock socket
    vi.mocked(io).mockReturnValue(mockSocket);

    // Clear any existing listeners
    (wsService as any).listeners.clear();
    (wsService as any).socket = null;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('connect', () => {
    it('should create a new socket connection', () => {
      wsService.connect();

      expect(io).toHaveBeenCalledWith(
        expect.stringContaining('ws://'),
        expect.objectContaining({
          transports: ['websocket'],
        })
      );
    });

    it('should not create duplicate connections', () => {
      wsService.connect();
      wsService.connect();

      expect(io).toHaveBeenCalledTimes(1);
    });

    it('should set up event listeners', () => {
      wsService.connect();

      expect(mockSocket.on).toHaveBeenCalledWith('connect', expect.any(Function));
      expect(mockSocket.on).toHaveBeenCalledWith('disconnect', expect.any(Function));
      expect(mockSocket.on).toHaveBeenCalledWith('error', expect.any(Function));
      expect(mockSocket.on).toHaveBeenCalledWith('document_created', expect.any(Function));
      expect(mockSocket.on).toHaveBeenCalledWith('document_updated', expect.any(Function));
      expect(mockSocket.on).toHaveBeenCalledWith('document_deleted', expect.any(Function));
      expect(mockSocket.on).toHaveBeenCalledWith('processing_progress', expect.any(Function));
      expect(mockSocket.on).toHaveBeenCalledWith('system_notification', expect.any(Function));
    });

    it('should handle connect event', () => {
      const consoleSpy = vi.spyOn(console, 'log').mockImplementation();
      wsService.connect();

      // Get the connect handler and call it
      const connectHandler = mockSocket.on.mock.calls.find(call => call[0] === 'connect')?.[1];
      mockSocket.connected = true;
      connectHandler?.();

      expect(consoleSpy).toHaveBeenCalledWith('WebSocket connected');
      consoleSpy.mockRestore();
    });

    it('should handle disconnect event', () => {
      const consoleSpy = vi.spyOn(console, 'log').mockImplementation();
      wsService.connect();

      // Get the disconnect handler and call it
      const disconnectHandler = mockSocket.on.mock.calls.find(call => call[0] === 'disconnect')?.[1];
      mockSocket.connected = false;
      disconnectHandler?.();

      expect(consoleSpy).toHaveBeenCalledWith('WebSocket disconnected');
      consoleSpy.mockRestore();
    });

    it('should handle error event', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation();
      wsService.connect();

      // Get the error handler and call it
      const errorHandler = mockSocket.on.mock.calls.find(call => call[0] === 'error')?.[1];
      const error = new Error('Connection error');
      errorHandler?.(error);

      expect(consoleSpy).toHaveBeenCalledWith('WebSocket error:', error);
      consoleSpy.mockRestore();
    });
  });

  describe('disconnect', () => {
    it('should disconnect the socket', () => {
      wsService.connect();
      wsService.disconnect();

      expect(mockSocket.disconnect).toHaveBeenCalled();
      expect((wsService as any).socket).toBeNull();
    });

    it('should handle disconnect when not connected', () => {
      wsService.disconnect();
      expect(mockSocket.disconnect).not.toHaveBeenCalled();
    });
  });

  describe('isConnected', () => {
    it('should return false when not connected', () => {
      expect(wsService.isConnected()).toBe(false);
    });

    it('should return true when connected', () => {
      wsService.connect();
      mockSocket.connected = true;
      expect(wsService.isConnected()).toBe(true);
    });
  });

  describe('event subscription', () => {
    describe('onDocumentCreated', () => {
      it('should subscribe to document created events', () => {
        const callback = vi.fn();
        const unsubscribe = wsService.onDocumentCreated(callback);

        // Simulate an event
        wsService.connect();
        const handler = mockSocket.on.mock.calls.find(call => call[0] === 'document_created')?.[1];
        handler?.(mockDocument);

        expect(callback).toHaveBeenCalledWith(mockDocument);

        // Test unsubscribe
        unsubscribe();
        callback.mockClear();
        handler?.(mockDocument);
        expect(callback).not.toHaveBeenCalled();
      });
    });

    describe('onDocumentUpdated', () => {
      it('should subscribe to document updated events', () => {
        const callback = vi.fn();
        const unsubscribe = wsService.onDocumentUpdated(callback);

        wsService.connect();
        const handler = mockSocket.on.mock.calls.find(call => call[0] === 'document_updated')?.[1];
        handler?.(mockDocument);

        expect(callback).toHaveBeenCalledWith(mockDocument);

        unsubscribe();
        callback.mockClear();
        handler?.(mockDocument);
        expect(callback).not.toHaveBeenCalled();
      });
    });

    describe('onDocumentDeleted', () => {
      it('should subscribe to document deleted events', () => {
        const callback = vi.fn();
        const documentId = 'doc-123';
        const unsubscribe = wsService.onDocumentDeleted(callback);

        wsService.connect();
        const handler = mockSocket.on.mock.calls.find(call => call[0] === 'document_deleted')?.[1];
        handler?.({ document_id: documentId });

        expect(callback).toHaveBeenCalledWith(documentId);

        unsubscribe();
        callback.mockClear();
        handler?.({ document_id: documentId });
        expect(callback).not.toHaveBeenCalled();
      });
    });

    describe('onProcessingProgress', () => {
      it('should subscribe to processing progress events', () => {
        const callback = vi.fn();
        const progress = { document_id: 'doc-123', progress: 50, status: 'processing' };
        const unsubscribe = wsService.onProcessingProgress(callback);

        wsService.connect();
        const handler = mockSocket.on.mock.calls.find(call => call[0] === 'processing_progress')?.[1];
        handler?.(progress);

        expect(callback).toHaveBeenCalledWith(progress);

        unsubscribe();
        callback.mockClear();
        handler?.(progress);
        expect(callback).not.toHaveBeenCalled();
      });
    });

    describe('onSystemNotification', () => {
      it('should subscribe to system notification events', () => {
        const callback = vi.fn();
        const notification = mockWebSocketEvents.systemNotification;
        const unsubscribe = wsService.onSystemNotification(callback);

        wsService.connect();
        const handler = mockSocket.on.mock.calls.find(call => call[0] === 'system_notification')?.[1];
        handler?.(notification);

        expect(callback).toHaveBeenCalledWith(notification);

        unsubscribe();
        callback.mockClear();
        handler?.(notification);
        expect(callback).not.toHaveBeenCalled();
      });
    });
  });

  describe('event emission', () => {
    describe('emit', () => {
      it('should emit events when connected', () => {
        wsService.connect();
        mockSocket.connected = true;

        wsService.emit('custom_event', { data: 'test' });

        expect(mockSocket.emit).toHaveBeenCalledWith('custom_event', { data: 'test' });
      });

      it('should not emit events when not connected', () => {
        const consoleSpy = vi.spyOn(console, 'warn').mockImplementation();

        wsService.emit('custom_event', { data: 'test' });

        expect(mockSocket.emit).not.toHaveBeenCalled();
        expect(consoleSpy).toHaveBeenCalledWith('WebSocket is not connected');

        consoleSpy.mockRestore();
      });
    });
  });

  describe('multiple listeners', () => {
    it('should support multiple listeners for the same event', () => {
      const callback1 = vi.fn();
      const callback2 = vi.fn();

      wsService.onDocumentCreated(callback1);
      wsService.onDocumentCreated(callback2);

      wsService.connect();
      const handler = mockSocket.on.mock.calls.find(call => call[0] === 'document_created')?.[1];
      handler?.(mockDocument);

      expect(callback1).toHaveBeenCalledWith(mockDocument);
      expect(callback2).toHaveBeenCalledWith(mockDocument);
    });

    it('should handle listener removal correctly', () => {
      const callback1 = vi.fn();
      const callback2 = vi.fn();

      const unsubscribe1 = wsService.onDocumentCreated(callback1);
      const unsubscribe2 = wsService.onDocumentCreated(callback2);

      wsService.connect();
      const handler = mockSocket.on.mock.calls.find(call => call[0] === 'document_created')?.[1];

      // Remove first listener
      unsubscribe1();

      handler?.(mockDocument);

      expect(callback1).not.toHaveBeenCalled();
      expect(callback2).toHaveBeenCalledWith(mockDocument);
    });
  });

  describe('error handling', () => {
    it('should handle socket errors gracefully', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation();
      const callback = vi.fn();

      wsService.onDocumentCreated(callback);
      wsService.connect();

      const handler = mockSocket.on.mock.calls.find(call => call[0] === 'document_created')?.[1];

      // Simulate an error in the callback
      callback.mockImplementation(() => {
        throw new Error('Callback error');
      });

      // Should not throw
      expect(() => handler?.(mockDocument)).not.toThrow();

      consoleSpy.mockRestore();
    });
  });
});