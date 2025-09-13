import { describe, it, expect, vi, beforeEach } from 'vitest';
import axios from 'axios';

// Mock localStorage before importing api
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  writable: true
});

// Mock axios
vi.mock('axios');

// Mock the api instance with interceptors
const mockApi = {
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  delete: vi.fn(),
  interceptors: {
    request: {
      use: vi.fn()
    },
    response: {
      use: vi.fn()
    }
  }
};

// Override the create method to return our mock
vi.mocked(axios).create = vi.fn(() => mockApi as any);

// Now import api after mocks are set up
import { documentApi, searchApi, processApi, healthApi } from './api';
import { mockDocument, mockDocuments, mockSearchResults } from '../test/mocks';

describe('API Service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('documentApi', () => {
    describe('uploadDocument', () => {
      it('should upload a document successfully', async () => {
        const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
        const formData = new FormData();
        formData.append('file', file);

        mockApi.post.mockResolvedValueOnce({ data: mockDocument });

        const result = await documentApi.uploadDocument(file);

        expect(mockApi.post).toHaveBeenCalledWith('/api/documents/upload', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
        expect(result).toEqual(mockDocument);
      });

      it('should handle upload errors', async () => {
        const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
        const error = new Error('Upload failed');

        mockApi.post.mockRejectedValueOnce(error);

        await expect(documentApi.uploadDocument(file)).rejects.toThrow('Upload failed');
      });

      it('should handle actual backend upload response format with id field', async () => {
        const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });

        // Test the actual response format from backend
        const backendUploadResponse = {
          id: 'doc-123',  // Backend returns 'id' field
          metadata: {
            document_id: 'doc-123',
            name: 'test.pdf',
            document_type: 'pdf',
            version: 1,
            size: 1024,
            created_at: '2025-01-01T00:00:00',
            updated_at: '2025-01-01T00:00:00',
            user_id: 'user-123',
            tags: [],
            processing_status: 'completed'
          },
          content: {
            raw_content: 'Test content',
            formatted_content: 'Test content',
            summary: null
          }
        };

        mockApi.post.mockResolvedValueOnce({ data: backendUploadResponse });

        const result = await documentApi.uploadDocument(file);

        expect(result).toEqual(backendUploadResponse);
        expect(result).toHaveProperty('id');  // Frontend expects this field
        expect(result.id).toBe('doc-123');
      });
    });

    describe('createDocument', () => {
      it('should create a document successfully', async () => {
        mockApi.post.mockResolvedValueOnce({ data: mockDocument });

        const result = await documentApi.createDocument(mockDocument);

        expect(mockApi.post).toHaveBeenCalledWith('/api/documents', mockDocument);
        expect(result).toEqual(mockDocument);
      });
    });

    describe('listDocuments', () => {
      it('should list documents successfully', async () => {
        mockApi.get.mockResolvedValueOnce({ data: mockDocuments });

        const result = await documentApi.listDocuments();

        expect(mockApi.get).toHaveBeenCalledWith('/api/documents');
        expect(result).toEqual(mockDocuments);
      });

      it('should handle empty document list', async () => {
        mockApi.get.mockResolvedValueOnce({ data: [] });

        const result = await documentApi.listDocuments();

        expect(result).toEqual([]);
      });

      it('should handle backend response format with documents wrapper', async () => {
        // Test the actual backend response format
        const backendResponse = {
          documents: mockDocuments,
          total: 2,
          limit: 10,
          offset: 0
        };
        mockApi.get.mockResolvedValueOnce({ data: backendResponse });

        const result = await documentApi.listDocuments();

        expect(mockApi.get).toHaveBeenCalledWith('/api/documents/', { params: undefined });
        expect(result).toEqual(mockDocuments); // Should extract documents array
      });

      it('should handle documents with nested metadata/content structure', async () => {
        // Test the actual nested structure from backend
        const nestedDocuments = [{
          metadata: {
            document_id: 'doc-123',
            name: 'test.pdf',
            document_type: 'pdf',
            version: 1,
            size: 0,
            created_at: '2025-01-01T00:00:00',
            updated_at: '2025-01-01T00:00:00',
            user_id: 'user-123',
            tags: [],
            processing_status: 'completed'
          },
          content: {
            summary: 'Test summary'
          }
        }];

        const backendResponse = {
          documents: nestedDocuments,
          total: 1,
          limit: 10,
          offset: 0
        };
        mockApi.get.mockResolvedValueOnce({ data: backendResponse });

        const result = await documentApi.listDocuments();

        expect(result).toEqual(nestedDocuments);
      });
    });

    describe('getDocument', () => {
      it('should get a document by ID', async () => {
        const documentId = 'doc-123';
        mockApi.get.mockResolvedValueOnce({ data: mockDocument });

        const result = await documentApi.getDocument(documentId);

        expect(mockApi.get).toHaveBeenCalledWith(`/api/documents/${documentId}`);
        expect(result).toEqual(mockDocument);
      });

      it('should handle document not found', async () => {
        const documentId = 'non-existent';
        const error = { response: { status: 404, data: { detail: 'Document not found' } } };

        mockApi.get.mockRejectedValueOnce(error);

        await expect(documentApi.getDocument(documentId)).rejects.toEqual(error);
      });
    });

    describe('updateDocument', () => {
      it('should update a document successfully', async () => {
        const documentId = 'doc-123';
        const updatedDocument = { ...mockDocument, metadata: { ...mockDocument.metadata, name: 'updated.pdf' } };

        mockApi.put.mockResolvedValueOnce({ data: updatedDocument });

        const result = await documentApi.updateDocument(documentId, updatedDocument);

        expect(mockApi.put).toHaveBeenCalledWith(`/api/documents/${documentId}`, updatedDocument);
        expect(result).toEqual(updatedDocument);
      });
    });

    describe('deleteDocument', () => {
      it('should delete a document successfully', async () => {
        const documentId = 'doc-123';
        mockApi.delete.mockResolvedValueOnce({ data: null });

        await documentApi.deleteDocument(documentId);

        expect(mockApi.delete).toHaveBeenCalledWith(`/api/documents/${documentId}`);
      });
    });

    describe('getDocumentVersions', () => {
      it('should get document versions', async () => {
        const documentId = 'doc-123';
        const versions = [mockDocument];

        mockApi.get.mockResolvedValueOnce({ data: versions });

        const result = await documentApi.getDocumentVersions(documentId);

        expect(mockApi.get).toHaveBeenCalledWith(`/api/documents/${documentId}/versions`);
        expect(result).toEqual(versions);
      });
    });
  });

  describe('searchApi', () => {
    const searchQuery = { query: 'test query', limit: 10 };

    describe('vectorSearch', () => {
      it('should perform vector search successfully', async () => {
        mockApi.post.mockResolvedValueOnce({ data: mockSearchResults });

        const result = await searchApi.vectorSearch(searchQuery);

        expect(mockApi.post).toHaveBeenCalledWith('/api/search/vector', searchQuery);
        expect(result).toEqual(mockSearchResults);
      });

      it('should handle actual backend search response format', async () => {
        // Test the actual format returned by our backend
        const backendSearchResults = [{
          document_id: 'doc-123',
          score: 0.85,
          metadata: {
            document_id: 'doc-123',
            name: 'test.pdf',
            document_type: 'pdf',
            version: 1,
            size: 0,
            created_at: '2025-01-01T00:00:00',
            updated_at: '2025-01-01T00:00:00',
            user_id: 'user-123',
            tags: [],
            processing_status: 'completed'
          },
          highlights: ['...test...']
        }];

        mockApi.post.mockResolvedValueOnce({ data: backendSearchResults });

        const result = await searchApi.vectorSearch(searchQuery);

        expect(mockApi.post).toHaveBeenCalledWith('/api/search/vector', searchQuery);
        expect(result).toEqual(backendSearchResults);
        expect(result[0]).toHaveProperty('document_id');
        expect(result[0]).toHaveProperty('score');
        expect(result[0]).toHaveProperty('metadata');
        expect(result[0]).toHaveProperty('highlights');
      });
    });

    describe('fulltextSearch', () => {
      it('should perform fulltext search successfully', async () => {
        // Backend returns SearchResponse with results property
        mockApi.post.mockResolvedValueOnce({ data: { results: mockSearchResults } });

        const result = await searchApi.fulltextSearch(searchQuery);

        expect(mockApi.post).toHaveBeenCalledWith('/api/search/fulltext', searchQuery);
        expect(result).toEqual(mockSearchResults);
      });
    });

    describe('graphSearch', () => {
      it('should perform graph search successfully', async () => {
        // Backend returns SearchResponse with results property
        mockApi.post.mockResolvedValueOnce({ data: { results: mockSearchResults } });

        const result = await searchApi.graphSearch(searchQuery);

        expect(mockApi.post).toHaveBeenCalledWith('/api/search/graph', searchQuery);
        expect(result).toEqual(mockSearchResults);
      });
    });

    describe('hybridSearch', () => {
      it('should perform hybrid search successfully', async () => {
        mockApi.post.mockResolvedValueOnce({ data: mockSearchResults });

        const result = await searchApi.hybridSearch(searchQuery);

        expect(mockApi.post).toHaveBeenCalledWith('/api/search/hybrid', searchQuery);
        expect(result).toEqual(mockSearchResults);
      });
    });

    it('should handle search errors', async () => {
      const error = new Error('Search failed');
      mockApi.post.mockRejectedValueOnce(error);

      await expect(searchApi.vectorSearch(searchQuery)).rejects.toThrow('Search failed');
    });

    it('should handle empty search results', async () => {
      mockApi.post.mockResolvedValueOnce({ data: [] });

      const result = await searchApi.vectorSearch(searchQuery);

      expect(result).toEqual([]);
    });
  });

  describe('processApi', () => {
    describe('pdfToMarkdown', () => {
      it('should convert PDF to markdown', async () => {
        const file = new File(['pdf content'], 'test.pdf', { type: 'application/pdf' });
        const formData = new FormData();
        formData.append('file', file);

        mockApi.post.mockResolvedValueOnce({ data: { markdown: '# Converted Content' } });

        const result = await processApi.pdfToMarkdown(file);

        expect(mockApi.post).toHaveBeenCalledWith('/api/process/pdf-to-markdown', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
        expect(result).toEqual({ markdown: '# Converted Content' });
      });
    });

    describe('transcribe', () => {
      it('should transcribe media URL', async () => {
        const mediaUrl = 'https://example.com/video.mp4';
        const transcription = { text: 'Transcribed content' };

        mockApi.post.mockResolvedValueOnce({ data: transcription });

        const result = await processApi.transcribe(mediaUrl);

        expect(mockApi.post).toHaveBeenCalledWith('/api/process/transcribe', { url: mediaUrl });
        expect(result).toEqual(transcription);
      });
    });

    describe('scrape', () => {
      it('should scrape webpage', async () => {
        const url = 'https://example.com';
        const scraped = { content: 'Scraped content', markdown: '# Page Title' };

        mockApi.post.mockResolvedValueOnce({ data: scraped });

        const result = await processApi.scrape(url);

        expect(mockApi.post).toHaveBeenCalledWith('/api/process/scrape', { url });
        expect(result).toEqual(scraped);
      });
    });

    describe('summarize', () => {
      it('should summarize document', async () => {
        const documentId = 'doc-123';
        const summary = { summary: 'Document summary' };

        mockApi.post.mockResolvedValueOnce({ data: summary });

        const result = await processApi.summarize(documentId);

        expect(mockApi.post).toHaveBeenCalledWith('/api/process/summarize', { document_id: documentId });
        expect(result).toEqual(summary);
      });
    });

    describe('extractEntities', () => {
      it('should extract entities from document', async () => {
        const documentId = 'doc-123';
        const entities = { entities: ['Person1', 'Organization1', 'Location1'] };

        mockApi.post.mockResolvedValueOnce({ data: entities });

        const result = await processApi.extractEntities(documentId);

        expect(mockApi.post).toHaveBeenCalledWith('/api/process/extract-entities', { document_id: documentId });
        expect(result).toEqual(entities);
      });
    });
  });

  describe('healthApi', () => {
    describe('checkHealth', () => {
      it('should check health successfully', async () => {
        const healthStatus = { status: 'healthy', services: {} };
        mockApi.get.mockResolvedValueOnce({ data: healthStatus });

        const result = await healthApi.checkHealth();

        expect(mockApi.get).toHaveBeenCalledWith('/api/health');
        expect(result).toEqual(healthStatus);
      });

      it('should handle health check failure', async () => {
        const error = new Error('Service unavailable');
        mockApi.get.mockRejectedValueOnce(error);

        await expect(healthApi.checkHealth()).rejects.toThrow('Service unavailable');
      });
    });

    describe('checkReadiness', () => {
      it('should check readiness successfully', async () => {
        const readinessStatus = { ready: true };
        mockApi.get.mockResolvedValueOnce({ data: readinessStatus });

        const result = await healthApi.checkReadiness();

        expect(mockApi.get).toHaveBeenCalledWith('/api/ready');
        expect(result).toEqual(readinessStatus);
      });
    });

    describe('getMetrics', () => {
      it('should get metrics successfully', async () => {
        const metrics = { requests: 100, errors: 2, latency: 50 };
        mockApi.get.mockResolvedValueOnce({ data: metrics });

        const result = await healthApi.getMetrics();

        expect(mockApi.get).toHaveBeenCalledWith('/api/metrics');
        expect(result).toEqual(metrics);
      });
    });
  });
});