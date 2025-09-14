/**
 * Debug utilities for WebSocket and document upload troubleshooting
 */
import { wsService } from '../services/websocket';
import { documentApi } from '../services/api';
import { logger } from '../services/logging';

interface DebugInfo {
  websocket: {
    connected: boolean;
    info: any;
    registeredEvents: any;
  };
  api: {
    baseUrl: string;
  };
  localStorage: {
    apiKey: string | null;
    [key: string]: any;
  };
}

class DebugHelper {
  /**
   * Get comprehensive debug information
   */
  getDebugInfo(): DebugInfo {
    const timestamp = new Date().toISOString();
    logger.info(`[DEBUG ${timestamp}] Getting debug information`);

    const debugInfo: DebugInfo = {
      websocket: {
        connected: wsService.isConnected(),
        info: wsService.getConnectionInfo(),
        registeredEvents: wsService.getRegisteredEvents()
      },
      api: {
        baseUrl: documentApi.defaults?.baseURL || 'unknown'
      },
      localStorage: {
        apiKey: localStorage.getItem('apiKey'),
        ...this.getAllLocalStorageItems()
      }
    };

    logger.info(`[DEBUG ${timestamp}] Debug info collected`, debugInfo);
    return debugInfo;
  }

  /**
   * Test WebSocket connection
   */
  async testWebSocket(): Promise<boolean> {
    const timestamp = new Date().toISOString();
    logger.info(`[DEBUG ${timestamp}] Starting WebSocket test`);

    if (!wsService.isConnected()) {
      logger.warn(`[DEBUG ${timestamp}] WebSocket not connected - attempting to connect`);
      try {
        wsService.connect();
        // Wait a bit for connection to establish
        await new Promise(resolve => setTimeout(resolve, 2000));
      } catch (error) {
        logger.error(`[DEBUG ${timestamp}] Failed to connect WebSocket`, error);
        return false;
      }
    }

    return await wsService.testConnection();
  }

  /**
   * Test document API connection
   */
  async testDocumentApi(): Promise<boolean> {
    const timestamp = new Date().toISOString();
    logger.info(`[DEBUG ${timestamp}] Testing document API`);

    try {
      const documents = await documentApi.listDocuments();
      logger.info(`[DEBUG ${timestamp}] API test successful`, {
        documentsCount: Array.isArray(documents) ? documents.length : 0,
        documentsType: typeof documents
      });
      return true;
    } catch (error: any) {
      logger.error(`[DEBUG ${timestamp}] API test failed`, {
        error: error.message,
        status: error.response?.status,
        data: error.response?.data
      });
      return false;
    }
  }

  /**
   * Run comprehensive diagnostics
   */
  async runDiagnostics() {
    const timestamp = new Date().toISOString();
    logger.info(`[DEBUG ${timestamp}] Starting comprehensive diagnostics`);

    console.group('🔍 Mavn Bench Debug Diagnostics');

    // 1. Basic info
    console.log('📊 Debug Information:', this.getDebugInfo());

    // 2. Test WebSocket
    console.log('🌐 Testing WebSocket connection...');
    const wsTest = await this.testWebSocket();
    console.log(`WebSocket test: ${wsTest ? '✅ PASS' : '❌ FAIL'}`);

    // 3. Test API
    console.log('🔗 Testing Document API...');
    const apiTest = await this.testDocumentApi();
    console.log(`API test: ${apiTest ? '✅ PASS' : '❌ FAIL'}`);

    // 4. WebSocket info
    if (wsService.isConnected()) {
      console.log('📡 WebSocket Connection Info:');
      console.table(wsService.getConnectionInfo());

      console.log('📋 Registered Event Listeners:');
      console.table(wsService.getRegisteredEvents().listenerDetails);
    }

    // 5. Recommendations
    console.log('💡 Recommendations:');
    if (!wsTest) {
      console.log('  • WebSocket connection failed - check if backend is running');
      console.log('  • Check VITE_WS_URL environment variable');
      console.log('  • Check browser console for connection errors');
    }
    if (!apiTest) {
      console.log('  • API connection failed - check if backend is running');
      console.log('  • Check API key in localStorage');
      console.log('  • Check CORS settings');
    }
    if (wsTest && apiTest) {
      console.log('  • All connections working - check event emission from backend');
      console.log('  • Upload a file and watch console logs');
    }

    console.groupEnd();

    logger.info(`[DEBUG ${timestamp}] Diagnostics completed`, {
      wsTest,
      apiTest,
      summary: 'Check browser console for detailed results'
    });

    return { wsTest, apiTest };
  }

  /**
   * Enable debug logging for all services
   */
  enableDebugLogging() {
    wsService.setDebugMode(true);
    logger.info('[DEBUG] Debug logging enabled for WebSocket service');
    console.log('🐛 Debug logging enabled. Upload a file to see detailed logs.');
  }

  /**
   * Disable debug logging
   */
  disableDebugLogging() {
    wsService.setDebugMode(false);
    logger.info('[DEBUG] Debug logging disabled for WebSocket service');
    console.log('🔇 Debug logging disabled.');
  }

  /**
   * Monitor WebSocket events in real-time
   */
  monitorWebSocketEvents() {
    const timestamp = new Date().toISOString();
    console.log(`🔍 Starting WebSocket event monitoring at ${timestamp}`);
    console.log('📡 Monitoring these events: system:notification, document:created, document:updated');

    // Monitor system notifications
    const unsubscribeSystem = wsService.onSystemNotification((notification) => {
      console.log('📢 SYSTEM NOTIFICATION:', notification);
    });

    // Monitor document events
    const unsubscribeCreated = wsService.onDocumentCreated((data) => {
      console.log('📄 DOCUMENT CREATED:', data);
    });

    const unsubscribeUpdated = wsService.onDocumentUpdated((data) => {
      console.log('📝 DOCUMENT UPDATED:', data);
    });

    // Return cleanup function
    return () => {
      console.log('🔇 Stopping WebSocket event monitoring');
      unsubscribeSystem();
      unsubscribeCreated();
      unsubscribeUpdated();
    };
  }

  private getAllLocalStorageItems() {
    const items: { [key: string]: any } = {};
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key) {
        items[key] = localStorage.getItem(key);
      }
    }
    return items;
  }
}

// Create global instance
export const debugHelper = new DebugHelper();

// Expose to window for browser console access
declare global {
  interface Window {
    mavnDebug: DebugHelper;
  }
}

window.mavnDebug = debugHelper;

// Log availability
console.log('🔧 Mavn Bench Debug Helper loaded. Use window.mavnDebug or:');
console.log('  • mavnDebug.runDiagnostics() - Run full diagnostics');
console.log('  • mavnDebug.testWebSocket() - Test WebSocket connection');
console.log('  • mavnDebug.testDocumentApi() - Test API connection');
console.log('  • mavnDebug.enableDebugLogging() - Enable verbose logging');
console.log('  • mavnDebug.monitorWebSocketEvents() - Monitor events in real-time');