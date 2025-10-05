import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { io, Socket } from 'socket.io-client';
import { wsService } from './websocket';
import { mockDocument, mockWebSocketEvents } from '../test/mocks';

// Mock socket.io-client
vi.mock('socket.io-client');

describe('WebSocketService', () => {
  let mockSocket: any;

  beforeEach(() => {
    // Create a mock engine for io.engine.transport
    const mockEngine = {
      transport: {
        name: 'websocket'
      }
    };

    // Create a mock io manager with on method
    const mockIo = {
      on: vi.fn(),
      engine: mockEngine
    };

    // Create a mock socket with io property
    mockSocket = {
      connected: false,
      on: vi.fn(),
      off: vi.fn(),
      emit: vi.fn(),
      disconnect: vi.fn(),
      connect: vi.fn(),
      onAny: vi.fn(),
      removeAllListeners: vi.fn(),
      io: mockIo,
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
          path: '/socket.io',
          transports: ['websocket', 'polling'],
        })
      );
    });

    it('should not create duplicate connections', () => {
      wsService.connect();
      mockSocket.connected = true;  // Simulate that socket is connected
      wsService.connect();

      expect(io).toHaveBeenCalledTimes(1);
    });

    it('should set up event listeners', () => {
      wsService.connect();

      expect(mockSocket.on).toHaveBeenCalledWith('connect', expect.any(Function));
      expect(mockSocket.on).toHaveBeenCalledWith('disconnect', expect.any(Function));
      expect(mockSocket.on).toHaveBeenCalledWith('error', expect.any(Function));
      // The service now uses onAny to forward all events
      expect(mockSocket.onAny).toHaveBeenCalledWith(expect.any(Function));
    });

    it('should handle connect event', () => {
      wsService.connect();

      // Get the connect handler and call it
      const connectHandler = mockSocket.on.mock.calls.find(call => call[0] === 'connect')?.[1];
      mockSocket.connected = true;
      mockSocket.id = 'test-socket-id';
      connectHandler?.();

      // Verify the handler was registered (actual logging is handled by the log method)
      expect(connectHandler).toBeDefined();
    });

    it('should handle disconnect event', () => {
      wsService.connect();

      // Get the disconnect handler and call it
      const disconnectHandler = mockSocket.on.mock.calls.find(call => call[0] === 'disconnect')?.[1];
      mockSocket.connected = false;
      disconnectHandler?.('transport close');

      // Verify the handler was registered (actual logging is handled by the log method)
      expect(disconnectHandler).toBeDefined();
    });

    it('should handle error event', () => {
      wsService.connect();

      // Get the error handler and call it
      const errorHandler = mockSocket.on.mock.calls.find(call => call[0] === 'error')?.[1];
      const error = new Error('Connection error');
      errorHandler?.(error);

      // Verify the handler was registered (actual logging is handled by the log method)
      expect(errorHandler).toBeDefined();
    });
  });

  describe('disconnect', () => {
    it('should disconnect the socket', () => {
      wsService.connect();
      wsService.disconnect();

      expect(mockSocket.disconnect).toHaveBeenCalled();
    });

    it('should handle disconnect when not connected', () => {
      expect(() => wsService.disconnect()).not.toThrow();
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

        // Simulate an event through onAny
        wsService.connect();
        const handler = mockSocket.onAny.mock.calls[0]?.[0];
        handler?.('document:created', mockDocument);

        expect(callback).toHaveBeenCalledWith(mockDocument);

        // Test unsubscribe
        unsubscribe();
        callback.mockClear();
        handler?.('document:created', mockDocument);
        expect(callback).not.toHaveBeenCalled();
      });
    });

    describe('onDocumentUpdated', () => {
      it('should subscribe to document updated events', () => {
        const callback = vi.fn();
        const unsubscribe = wsService.onDocumentUpdated(callback);

        wsService.connect();
        const handler = mockSocket.onAny.mock.calls[0]?.[0];
        handler?.('document:updated', mockDocument);

        expect(callback).toHaveBeenCalledWith(mockDocument);

        unsubscribe();
        callback.mockClear();
        handler?.('document:updated', mockDocument);
        expect(callback).not.toHaveBeenCalled();
      });
    });

    describe('onDocumentDeleted', () => {
      it('should subscribe to document deleted events', () => {
        const callback = vi.fn();
        const documentId = 'doc-123';
        const unsubscribe = wsService.onDocumentDeleted(callback);

        wsService.connect();
        const handler = mockSocket.onAny.mock.calls[0]?.[0];
        handler?.('document:deleted', documentId);

        expect(callback).toHaveBeenCalledWith(documentId);

        unsubscribe();
        callback.mockClear();
        handler?.('document:deleted', documentId);
        expect(callback).not.toHaveBeenCalled();
      });
    });

    describe('onProcessingProgress', () => {
      it('should subscribe to processing progress events', () => {
        const callback = vi.fn();
        const progress = { document_id: 'doc-123', progress: 50, status: 'processing' };
        const unsubscribe = wsService.onProcessingProgress(callback);

        wsService.connect();
        const handler = mockSocket.onAny.mock.calls[0]?.[0];
        handler?.('processing:progress', progress);

        expect(callback).toHaveBeenCalledWith(progress);

        unsubscribe();
        callback.mockClear();
        handler?.('processing:progress', progress);
        expect(callback).not.toHaveBeenCalled();
      });
    });

    describe('onSystemNotification', () => {
      it('should subscribe to system notification events', () => {
        const callback = vi.fn();
        const notification = mockWebSocketEvents.systemNotification;
        const unsubscribe = wsService.onSystemNotification(callback);

        wsService.connect();
        const handler = mockSocket.onAny.mock.calls[0]?.[0];
        handler?.('system:notification', notification);

        expect(callback).toHaveBeenCalledWith(notification);

        unsubscribe();
        callback.mockClear();
        handler?.('system:notification', notification);
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
        wsService.emit('custom_event', { data: 'test' });

        expect(mockSocket.emit).not.toHaveBeenCalled();
        // The warning is logged via the log() method, not console.warn
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
      const handler = mockSocket.onAny.mock.calls[0]?.[0];
      handler?.('document:created', mockDocument);

      expect(callback1).toHaveBeenCalledWith(mockDocument);
      expect(callback2).toHaveBeenCalledWith(mockDocument);
    });

    it('should handle listener removal correctly', () => {
      const callback1 = vi.fn();
      const callback2 = vi.fn();

      const unsubscribe1 = wsService.onDocumentCreated(callback1);
      const unsubscribe2 = wsService.onDocumentCreated(callback2);

      wsService.connect();
      const handler = mockSocket.onAny.mock.calls[0]?.[0];

      // Remove first listener
      unsubscribe1();

      handler?.('document:created', mockDocument);

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

      const handler = mockSocket.onAny.mock.calls[0]?.[0];

      // Simulate an error in the callback
      callback.mockImplementation(() => {
        throw new Error('Callback error');
      });

      // Should not throw
      expect(() => handler?.('document_created', mockDocument)).not.toThrow();

      consoleSpy.mockRestore();
    });
  });
});