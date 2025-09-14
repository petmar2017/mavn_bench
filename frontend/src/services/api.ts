import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor for authentication
api.interceptors.request.use((config) => {
  const apiKey = localStorage.getItem('apiKey');
  if (apiKey) {
    config.headers['X-API-Key'] = apiKey;
  }
  return config;
});

// Document types
export interface DocumentMetadata {
  document_id: string;
  name: string;
  document_type: string;
  version: number;
  size: number;
  created_at: string;
  updated_at: string;
  deleted?: boolean;
  deleted_at?: string | null;
  deleted_by?: string | null;
  user_id?: string;
  tags?: string[];
  source_url?: string;
  processing_status?: string;
  summary?: string;
  language?: string;
}

export interface DocumentContent {
  raw_content?: string;
  formatted_content?: string;
  summary?: string;
  entities?: Array<{ name: string; type: string; confidence: number }>;
  metadata?: Record<string, any>;
  embeddings?: number[];
}

export interface DocumentVersion {
  version: number;
  timestamp: string;
  user: string;
  changes: Record<string, any>;
  commit_message?: string;
}

export interface DocumentMessage {
  id?: string;  // ID field returned by upload endpoint
  metadata: DocumentMetadata;
  content: DocumentContent;
  tools?: string[];
  history?: DocumentVersion[];
  audit_log?: any[];
}

export interface SearchQuery {
  query: string;
  limit?: number;
  offset?: number;
  threshold?: number;
  filters?: Record<string, any>;
}

export interface SearchResult {
  document_id: string;
  score: number;
  metadata: DocumentMetadata;
  highlights?: string[];
}

// API methods
export const documentApi = {
  // Document CRUD
  async createDocument(formData: FormData) {
    const response = await api.post<DocumentMessage>('/api/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  async getDocument(documentId: string) {
    const response = await api.get<DocumentMessage>(`/api/documents/${documentId}`);
    return response.data;
  },

  async listDocuments(params?: { limit?: number; offset?: number; user_id?: string }) {
    const response = await api.get<{ documents: DocumentMessage[]; total: number; limit: number; offset: number }>('/api/documents/', { params });
    console.log('[API] Raw response from /api/documents/:', response.data);
    console.log('[API] Documents extracted:', response.data.documents);
    return response.data.documents || [];
  },

  async listDocumentsWithPagination(params?: { limit?: number; offset?: number; user_id?: string }) {
    const response = await api.get<{ documents: DocumentMessage[]; total: number; limit: number; offset: number }>('/api/documents/', { params });
    console.log('[API] Raw pagination response from /api/documents/:', response.data);
    return response.data;
  },

  async updateDocument(documentId: string, data: Partial<DocumentMessage>) {
    const response = await api.put<DocumentMessage>(`/api/documents/${documentId}`, data);
    return response.data;
  },

  async deleteDocument(documentId: string) {
    // Always use soft delete (backend defaults to soft_delete=true)
    const response = await api.delete(`/api/documents/${documentId}`);
    return response.data;
  },

  async listTrash() {
    const response = await api.get<{ documents: DocumentMessage[] }>('/api/documents/trash');
    return response.data.documents || [];
  },

  async restoreDocument(documentId: string) {
    // Restore a soft-deleted document by updating its deleted flag
    const response = await api.put(`/api/documents/${documentId}`, {
      metadata: {
        deleted: false,
        deleted_at: null,
        deleted_by: null
      }
    });
    return response.data;
  },

  async permanentlyDelete(documentId: string) {
    // Permanently delete a document (hard delete)
    const response = await api.delete(`/api/documents/${documentId}`, {
      params: { soft_delete: false }
    });
    return response.data;
  },

  // Version history methods
  async getDocumentVersions(documentId: string) {
    const response = await api.get<DocumentVersion[]>(`/api/documents/${documentId}/versions`);
    return response;
  },
};

export const searchApi = {
  async vectorSearch(query: SearchQuery) {
    const response = await api.post<SearchResult[]>('/api/search/vector', query);
    return response.data;
  },

  async fulltextSearch(query: SearchQuery) {
    try {
      const response = await api.post<SearchResult[] | { results: SearchResult[] }>('/api/search/fulltext', query);
      // Handle both direct array and wrapped response formats
      if (Array.isArray(response.data)) {
        return response.data;
      }
      return response.data.results || [];
    } catch (error: any) {
      // If there's a validation error, return empty array
      console.error('Fulltext search error:', error.response?.data);
      return [];
    }
  },

  async graphSearch(query: SearchQuery) {
    try {
      const response = await api.post<SearchResult[] | { results: SearchResult[] }>('/api/search/graph', query);
      // Handle both direct array and wrapped response formats
      if (Array.isArray(response.data)) {
        return response.data;
      }
      return response.data.results || [];
    } catch (error: any) {
      // If there's a validation error, return empty array
      console.error('Graph search error:', error.response?.data);
      return [];
    }
  },

  async hybridSearch(query: SearchQuery) {
    const response = await api.post<SearchResult[]>('/api/search/hybrid', query);
    return response.data;
  },

  async findSimilar(documentId: string, limit?: number) {
    const response = await api.get<SearchResult[]>(`/api/search/similar/${documentId}`, {
      params: { limit },
    });
    return response.data;
  },
};

export const processApi = {
  async pdfToMarkdown(formData: FormData) {
    const response = await api.post<{ markdown: string }>('/api/process/pdf-to-markdown', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  async transcribe(url: string, source: 'youtube' | 'podcast') {
    const response = await api.post<DocumentMessage>('/api/process/transcribe', { url, source });
    return response.data;
  },

  async scrapeWebpage(url: string) {
    const response = await api.post<DocumentMessage>('/api/process/scrape', { url });
    return response.data;
  },

  async summarize(documentId: string) {
    const response = await api.post<{ summary: string }>('/api/process/summarize', { document_id: documentId });
    return response.data;
  },

  async extractEntities(documentId: string) {
    const response = await api.post<{ entities: any[] }>('/api/process/extract-entities', { document_id: documentId });
    return response.data;
  },
};

export const healthApi = {
  async checkHealth() {
    const response = await api.get('/api/health');
    return response.data;
  },
};