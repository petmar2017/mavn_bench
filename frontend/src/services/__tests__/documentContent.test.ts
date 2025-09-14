import { describe, it, expect, beforeEach, vi } from 'vitest';
import { documentContentService } from '../documentContent';
import { api } from '../api';

// Mock the api module
vi.mock('../api', () => ({
  api: {
    get: vi.fn(),
    put: vi.fn()
  }
}));

describe('DocumentContentService', () => {
  beforeEach(() => {
    // Clear cache before each test
    documentContentService.clearAllCache();
    vi.clearAllMocks();
  });

  describe('getContent', () => {
    it('should fetch content from server on first request', async () => {
      const mockContent = {
        text: 'Test content',
        formatted_content: 'Formatted content',
        raw_text: 'Raw content',
        summary: 'Test summary'
      };

      const mockResponse = {
        data: {
          document_id: 'test-doc-1',
          content: mockContent
        }
      };

      vi.mocked(api.get).mockResolvedValueOnce(mockResponse);

      const result = await documentContentService.getContent('test-doc-1');

      expect(api.get).toHaveBeenCalledWith('/api/documents/test-doc-1/content');
      expect(result).toEqual(mockContent);
    });

    it('should use cached content on subsequent requests', async () => {
      const mockContent = {
        text: 'Cached content',
        formatted_content: 'Cached formatted',
        raw_text: 'Cached raw',
        summary: 'Cached summary'
      };

      const mockResponse = {
        data: {
          document_id: 'test-doc-2',
          content: mockContent
        }
      };

      vi.mocked(api.get).mockResolvedValueOnce(mockResponse);

      // First request - should fetch from server
      const result1 = await documentContentService.getContent('test-doc-2');
      expect(api.get).toHaveBeenCalledTimes(1);
      expect(result1).toEqual(mockContent);

      // Second request - should use cache
      const result2 = await documentContentService.getContent('test-doc-2');
      expect(api.get).toHaveBeenCalledTimes(1); // Still only called once
      expect(result2).toEqual(mockContent);
    });

    it('should handle concurrent requests for the same document', async () => {
      const mockContent = {
        text: 'Concurrent content',
        formatted_content: 'Concurrent formatted',
        raw_text: 'Concurrent raw',
        summary: 'Concurrent summary'
      };

      const mockResponse = {
        data: {
          document_id: 'test-doc-3',
          content: mockContent
        }
      };

      // Create a promise that we can control
      let resolvePromise: (value: any) => void;
      const controlledPromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });

      vi.mocked(api.get).mockReturnValueOnce(controlledPromise as any);

      // Start two concurrent requests
      const promise1 = documentContentService.getContent('test-doc-3');
      const promise2 = documentContentService.getContent('test-doc-3');

      // API should only be called once
      expect(api.get).toHaveBeenCalledTimes(1);

      // Resolve the API call
      resolvePromise!(mockResponse);

      const [result1, result2] = await Promise.all([promise1, promise2]);

      // Both should get the same result
      expect(result1).toEqual(mockContent);
      expect(result2).toEqual(mockContent);

      // API should still only be called once
      expect(api.get).toHaveBeenCalledTimes(1);
    });

    it('should handle errors and not cache them', async () => {
      const error = new Error('Network error');
      vi.mocked(api.get).mockRejectedValueOnce(error);

      // First request - should fail
      await expect(documentContentService.getContent('test-doc-4')).rejects.toThrow('Network error');

      // Mock successful response for retry
      const mockContent = {
        text: 'Success after error',
        formatted_content: 'Success formatted',
        raw_text: 'Success raw',
        summary: 'Success summary'
      };

      vi.mocked(api.get).mockResolvedValueOnce({
        data: {
          document_id: 'test-doc-4',
          content: mockContent
        }
      });

      // Second request - should try again (not cached error)
      const result = await documentContentService.getContent('test-doc-4');
      expect(result).toEqual(mockContent);
      expect(api.get).toHaveBeenCalledTimes(2);
    });
  });

  describe('updateContent', () => {
    it('should update content and clear cache', async () => {
      const mockContent = {
        text: 'Original content',
        formatted_content: 'Original formatted',
        raw_text: 'Original raw',
        summary: 'Original summary'
      };

      // First, populate the cache
      vi.mocked(api.get).mockResolvedValueOnce({
        data: {
          document_id: 'test-doc-5',
          content: mockContent
        }
      });

      await documentContentService.getContent('test-doc-5');

      // Mock the update call
      vi.mocked(api.put).mockResolvedValueOnce({});

      // Update the content
      await documentContentService.updateContent('test-doc-5', 'New content');

      // Verify PUT was called
      expect(api.put).toHaveBeenCalledWith('/api/documents/test-doc-5', {
        content: 'New content'
      });

      // Mock new content for next fetch
      const newMockContent = {
        text: 'New content',
        formatted_content: 'New formatted',
        raw_text: 'New raw',
        summary: 'New summary'
      };

      vi.mocked(api.get).mockResolvedValueOnce({
        data: {
          document_id: 'test-doc-5',
          content: newMockContent
        }
      });

      // Next getContent should fetch from server (cache cleared)
      const result = await documentContentService.getContent('test-doc-5');
      expect(api.get).toHaveBeenCalledTimes(2); // Called again after cache clear
      expect(result).toEqual(newMockContent);
    });
  });

  describe('clearCache', () => {
    it('should clear cache for specific document', async () => {
      const mockContent = {
        text: 'Cache test content',
        formatted_content: 'Cache test formatted',
        raw_text: 'Cache test raw',
        summary: 'Cache test summary'
      };

      vi.mocked(api.get).mockResolvedValue({
        data: {
          document_id: 'test-doc-6',
          content: mockContent
        }
      });

      // Populate cache
      await documentContentService.getContent('test-doc-6');
      expect(api.get).toHaveBeenCalledTimes(1);

      // Clear specific document cache
      documentContentService.clearCache('test-doc-6');

      // Next request should fetch from server
      await documentContentService.getContent('test-doc-6');
      expect(api.get).toHaveBeenCalledTimes(2);
    });
  });

  describe('preloadContent', () => {
    it('should preload multiple documents', async () => {
      const mockResponses = [
        {
          data: {
            document_id: 'preload-1',
            content: { text: 'Content 1' }
          }
        },
        {
          data: {
            document_id: 'preload-2',
            content: { text: 'Content 2' }
          }
        },
        {
          data: {
            document_id: 'preload-3',
            content: { text: 'Content 3' }
          }
        }
      ];

      vi.mocked(api.get)
        .mockResolvedValueOnce(mockResponses[0])
        .mockResolvedValueOnce(mockResponses[1])
        .mockResolvedValueOnce(mockResponses[2]);

      await documentContentService.preloadContent(['preload-1', 'preload-2', 'preload-3']);

      expect(api.get).toHaveBeenCalledTimes(3);
      expect(api.get).toHaveBeenCalledWith('/api/documents/preload-1/content');
      expect(api.get).toHaveBeenCalledWith('/api/documents/preload-2/content');
      expect(api.get).toHaveBeenCalledWith('/api/documents/preload-3/content');

      // Subsequent requests should use cache
      vi.mocked(api.get).mockClear();

      await documentContentService.getContent('preload-1');
      await documentContentService.getContent('preload-2');
      await documentContentService.getContent('preload-3');

      expect(api.get).not.toHaveBeenCalled();
    });
  });
});