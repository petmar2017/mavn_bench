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
  user_id?: string;
  tags?: string[];
  source_url?: string;
  processing_status?: string;
}

export interface DocumentContent {
  raw_content?: string;
  formatted_content?: string;
  summary?: string;
  entities?: Array<{ name: string; type: string; confidence: number }>;
  metadata?: Record<string, any>;
  embeddings?: number[];
}

export interface DocumentMessage {
  id?: string;  // ID field returned by upload endpoint
  metadata: DocumentMetadata;
  content: DocumentContent;
  tools?: string[];
  history?: any[];
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
    return response.data.documents || [];
  },

  async updateDocument(documentId: string, data: Partial<DocumentMessage>) {
    const response = await api.put<DocumentMessage>(`/api/documents/${documentId}`, data);
    return response.data;
  },

  async deleteDocument(documentId: string, hardDelete: boolean = true) {
    const response = await api.delete(`/api/documents/${documentId}`, {
      params: { soft_delete: !hardDelete }
    });
    return response.data;
  },
};

export const searchApi = {
  async vectorSearch(query: SearchQuery) {
    const response = await api.post<SearchResult[]>('/api/search/vector', query);
    return response.data;
  },

  async fulltextSearch(query: SearchQuery) {
    const response = await api.post<{ results: SearchResult[] }>('/api/search/fulltext', query);
    return response.data.results || [];
  },

  async graphSearch(query: SearchQuery) {
    const response = await api.post<{ results: SearchResult[] }>('/api/search/graph', query);
    return response.data.results || [];
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