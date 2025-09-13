// E2E Test Setup - No mocks, real backend integration
import { beforeAll, afterAll, beforeEach } from 'vitest';
import axios from 'axios';

const API_URL = 'http://localhost:8000';
const TEST_API_KEY = 'test-api-key-123';

// Setup axios instance for tests
export const testApi = axios.create({
  baseURL: API_URL,
  headers: {
    'X-API-Key': TEST_API_KEY,
  },
  timeout: 10000,
});

// Health check to ensure backend is running
export async function waitForBackend(retries = 10): Promise<void> {
  for (let i = 0; i < retries; i++) {
    try {
      const response = await axios.get(`${API_URL}/api/health`);
      if (response.status === 200) {
        console.log('✅ Backend is running');
        return;
      }
    } catch (error) {
      console.log(`Waiting for backend... (attempt ${i + 1}/${retries})`);
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
  }
  throw new Error('Backend is not responding. Make sure it is running on port 8000');
}

// Clean up test data
export async function cleanupTestData(): Promise<void> {
  try {
    // Get all documents
    const response = await testApi.get('/api/documents');
    const documents = response.data.documents || [];

    // Delete all test documents (those with names starting with 'test-')
    for (const doc of documents) {
      if (doc.metadata?.name?.startsWith('test-')) {
        await testApi.delete(`/api/documents/${doc.metadata.document_id}`);
      }
    }
    console.log('✅ Test data cleaned up');
  } catch (error) {
    console.warn('Could not clean up test data:', error);
  }
}

// Setup hooks
beforeAll(async () => {
  await waitForBackend();
  await cleanupTestData();
});

afterAll(async () => {
  await cleanupTestData();
});

beforeEach(async () => {
  // Clear any session storage or cookies
  if (typeof window !== 'undefined') {
    localStorage.clear();
    sessionStorage.clear();
  }
});

// Test utilities
export async function uploadTestFile(filename: string, content: string, type = 'text/plain'): Promise<any> {
  const blob = new Blob([content], { type });
  const formData = new FormData();
  formData.append('file', blob, filename);
  formData.append('name', filename);
  formData.append('type', type);

  const response = await testApi.post('/api/documents/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
}

export async function searchDocuments(query: string, searchType = 'vector'): Promise<any> {
  const response = await testApi.post(`/api/search/${searchType}`, {
    query,
    limit: 20,
  });

  return response.data;
}

export async function getDocument(documentId: string): Promise<any> {
  const response = await testApi.get(`/api/documents/${documentId}`);
  return response.data;
}

export async function listDocuments(): Promise<any[]> {
  const response = await testApi.get('/api/documents');
  return response.data.documents || [];
}

export async function deleteDocument(documentId: string): Promise<void> {
  await testApi.delete(`/api/documents/${documentId}`);
}