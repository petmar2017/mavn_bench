import { api } from './api';

export interface DocumentContent {
  text?: string;
  formatted_content?: string;
  raw_text?: string;
  summary?: string;
}

export interface DocumentContentResponse {
  document_id: string;
  content: DocumentContent;
}

// Cache for document content
const contentCache = new Map<string, {
  content: DocumentContent;
  timestamp: number;
  promise?: Promise<DocumentContent>;
}>();

// Cache TTL in milliseconds (5 minutes)
const CACHE_TTL = 5 * 60 * 1000;

/**
 * Service for fetching and caching document content
 */
export const documentContentService = {
  /**
   * Get document content with caching
   */
  async getContent(documentId: string): Promise<DocumentContent> {
    // Check cache first
    const cached = contentCache.get(documentId);
    if (cached) {
      // If there's a pending promise, return it
      if (cached.promise) {
        return cached.promise;
      }

      // Check if cache is still valid
      if (Date.now() - cached.timestamp < CACHE_TTL) {
        return cached.content;
      }
    }

    // Create a promise for this fetch to prevent duplicate requests
    const fetchPromise = this.fetchContent(documentId);

    // Store the promise in cache temporarily
    contentCache.set(documentId, {
      content: {},
      timestamp: Date.now(),
      promise: fetchPromise
    });

    try {
      const content = await fetchPromise;

      // Update cache with actual content
      contentCache.set(documentId, {
        content,
        timestamp: Date.now()
      });

      return content;
    } catch (error) {
      // Remove from cache on error
      contentCache.delete(documentId);
      throw error;
    }
  },

  /**
   * Fetch content from server
   */
  async fetchContent(documentId: string): Promise<DocumentContent> {
    const response = await api.get<DocumentContentResponse>(`/api/documents/${documentId}/content`);
    return response.data.content;
  },

  /**
   * Update document content
   */
  async updateContent(documentId: string, content: string): Promise<void> {
    await api.put(`/api/documents/${documentId}`, {
      content
    });

    // Invalidate cache
    contentCache.delete(documentId);
  },

  /**
   * Clear cache for a specific document
   */
  clearCache(documentId: string): void {
    contentCache.delete(documentId);
  },

  /**
   * Clear entire cache
   */
  clearAllCache(): void {
    contentCache.clear();
  },

  /**
   * Preload content for multiple documents
   */
  async preloadContent(documentIds: string[]): Promise<void> {
    const promises = documentIds.map(id => this.getContent(id).catch(() => {}));
    await Promise.all(promises);
  }
};