/**
 * Centralized API Configuration
 * All API endpoint and WebSocket configurations in one place
 */

// Default backend server URL
const DEFAULT_BACKEND_URL = 'http://localhost:8000';

// Determine the API base URL based on environment
export const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.DEV ? '' : DEFAULT_BACKEND_URL);

// Determine the WebSocket URL based on environment
export const WS_URL =
  import.meta.env.VITE_WS_URL ||
  (import.meta.env.DEV ? 'ws://localhost:8000' : DEFAULT_BACKEND_URL.replace('http', 'ws'));

// API endpoints configuration
export const API_ENDPOINTS = {
  // Document endpoints
  documents: '/api/documents/',
  documentById: (id: string) => `/api/documents/${id}/`,
  documentContent: (id: string) => `/api/documents/${id}/content/`,
  documentVersions: (id: string) => `/api/documents/${id}/versions/`,
  documentUpload: '/api/documents/upload/',

  // Processing endpoints
  processPdf: '/api/process/pdf-to-markdown/',
  processTranscribe: '/api/process/transcribe/',
  processScrape: '/api/process/scrape/',
  processSummarize: '/api/process/summarize/',
  processExtractEntities: '/api/process/extract-entities/',

  // Search endpoints
  searchVector: '/api/search/vector/',
  searchFulltext: '/api/search/fulltext/',
  searchGraph: '/api/search/graph/',

  // Queue endpoints
  queueStatus: '/api/queue/status/',
  queueWorkers: '/api/queue/workers/',

  // Client logging endpoint
  clientLogs: '/api/logs/client/',

  // WebSocket endpoint
  websocket: '/ws',
} as const;

// Authentication configuration
export const AUTH_CONFIG = {
  apiKeyHeader: 'X-API-Key',
  apiKeyStorageKey: 'apiKey',
  defaultApiKey: 'test_api_key_123456', // For development only
} as const;

// Request configuration
export const REQUEST_CONFIG = {
  timeout: 30000, // 30 seconds
  retries: 3,
  retryDelay: 1000, // 1 second
} as const;

// Pagination configuration
export const PAGINATION_CONFIG = {
  defaultLimit: 20,
  maxLimit: 100,
  defaultOffset: 0,
} as const;

export default {
  API_BASE_URL,
  WS_URL,
  API_ENDPOINTS,
  AUTH_CONFIG,
  REQUEST_CONFIG,
  PAGINATION_CONFIG,
};