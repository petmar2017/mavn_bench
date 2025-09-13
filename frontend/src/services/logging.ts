import axios from 'axios';

interface LogEntry {
  level: 'debug' | 'info' | 'warn' | 'error';
  message: string;
  timestamp: string;
  context?: any;
  stackTrace?: string;
  userAgent?: string;
  url?: string;
}

class ClientLogger {
  private buffer: LogEntry[] = [];
  private flushInterval = 5000; // Send logs every 5 seconds
  private maxBufferSize = 50;
  private flushTimer: NodeJS.Timeout | null = null;
  private isProduction = process.env.NODE_ENV === 'production';

  constructor() {
    // Start flush timer
    this.startFlushTimer();

    // Capture unhandled errors
    window.addEventListener('error', (event) => {
      this.error('Unhandled error', {
        message: event.message,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        error: event.error?.stack
      });
    });

    // Capture unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
      this.error('Unhandled promise rejection', {
        reason: event.reason,
        promise: event.promise
      });
    });

    // Flush logs before page unload
    window.addEventListener('beforeunload', () => {
      this.flush();
    });
  }

  private startFlushTimer() {
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
    }
    this.flushTimer = setInterval(() => this.flush(), this.flushInterval);
  }

  private log(level: LogEntry['level'], message: string, context?: any) {
    const entry: LogEntry = {
      level,
      message,
      timestamp: new Date().toISOString(),
      context,
      userAgent: navigator.userAgent,
      url: window.location.href,
    };

    // Add stack trace for errors
    if (level === 'error') {
      entry.stackTrace = new Error().stack;
    }

    // Always log to console
    const consoleMethod = level === 'debug' ? 'log' : level;
    console[consoleMethod](`[${level.toUpperCase()}] ${message}`, context);

    // Add to buffer
    this.buffer.push(entry);

    // Flush if buffer is full
    if (this.buffer.length >= this.maxBufferSize) {
      this.flush();
    }

    // Immediately send errors in production
    if (level === 'error' && this.isProduction) {
      this.flush();
    }
  }

  debug(message: string, context?: any) {
    // Only log debug in development
    if (!this.isProduction) {
      this.log('debug', message, context);
    }
  }

  info(message: string, context?: any) {
    this.log('info', message, context);
  }

  warn(message: string, context?: any) {
    this.log('warn', message, context);
  }

  error(message: string, context?: any) {
    this.log('error', message, context);
  }

  async flush() {
    if (this.buffer.length === 0) return;

    const logs = [...this.buffer];
    this.buffer = [];

    try {
      await axios.post('http://localhost:8000/api/client-logs', {
        logs,
        sessionId: this.getSessionId(),
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      // If logging fails, don't throw - just console error
      console.error('Failed to send logs to server:', error);

      // In development, keep trying to send logs
      if (!this.isProduction && logs.length > 0) {
        // Put critical logs back in buffer for retry (limit to prevent infinite growth)
        const criticalLogs = logs.filter(log => log.level === 'error').slice(-10);
        this.buffer = [...criticalLogs, ...this.buffer].slice(0, this.maxBufferSize);
      }
    }
  }

  private getSessionId(): string {
    let sessionId = sessionStorage.getItem('sessionId');
    if (!sessionId) {
      sessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      sessionStorage.setItem('sessionId', sessionId);
    }
    return sessionId;
  }

  // Method to manually flush logs
  forceFlush() {
    return this.flush();
  }

  // Method to clear buffer
  clearBuffer() {
    this.buffer = [];
  }

  // Method to get current buffer size
  getBufferSize(): number {
    return this.buffer.length;
  }
}

// Create singleton instance
export const logger = new ClientLogger();

// Export for use in error boundaries
export const logError = (error: Error, errorInfo?: any) => {
  logger.error('React Error Boundary', {
    error: error.toString(),
    stack: error.stack,
    componentStack: errorInfo?.componentStack,
    errorInfo
  });
};

// Helper function for API errors
export const logApiError = (endpoint: string, error: any) => {
  logger.error(`API Error: ${endpoint}`, {
    endpoint,
    status: error.response?.status,
    statusText: error.response?.statusText,
    data: error.response?.data,
    message: error.message,
    config: {
      method: error.config?.method,
      url: error.config?.url,
      headers: error.config?.headers,
    }
  });
};