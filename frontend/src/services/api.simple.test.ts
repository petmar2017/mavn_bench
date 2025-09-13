import axios from 'axios';
import { documentApi, searchApi } from './api';

// Mock axios
jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

// Mock the api instance
const mockApi = {
  get: jest.fn(),
  post: jest.fn(),
  put: jest.fn(),
  delete: jest.fn(),
};

// Override the create method to return our mock
mockedAxios.create = jest.fn(() => mockApi as any);

describe('API Service', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('documentApi', () => {
    it('should create a document', async () => {
      const mockDocument = { metadata: { document_id: '123' } };
      mockApi.post.mockResolvedValueOnce({ data: mockDocument });

      const formData = new FormData();
      const result = await documentApi.createDocument(formData);

      expect(mockApi.post).toHaveBeenCalledWith('/api/documents/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      expect(result).toEqual(mockDocument);
    });

    it('should list documents', async () => {
      const mockDocuments = [{ metadata: { document_id: '123' } }];
      mockApi.get.mockResolvedValueOnce({ data: mockDocuments });

      const result = await documentApi.listDocuments();

      expect(mockApi.get).toHaveBeenCalledWith('/api/documents', { params: undefined });
      expect(result).toEqual(mockDocuments);
    });
  });

  describe('searchApi', () => {
    it('should perform vector search', async () => {
      const mockResults = [{ document_id: '123', score: 0.9 }];
      mockApi.post.mockResolvedValueOnce({ data: mockResults });

      const query = { query: 'test', limit: 10 };
      const result = await searchApi.vectorSearch(query);

      expect(mockApi.post).toHaveBeenCalledWith('/api/search/vector', query);
      expect(result).toEqual(mockResults);
    });
  });
});