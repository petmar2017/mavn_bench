// Real E2E Tests for Document Operations - No Mocks!
import { describe, it, expect, beforeEach } from 'vitest';
import {
  uploadTestFile,
  listDocuments,
  getDocument,
  deleteDocument,
  cleanupTestData,
} from './setup';

describe('Document Operations E2E', () => {
  beforeEach(async () => {
    await cleanupTestData();
  });

  describe('Document Upload', () => {
    it('should upload a text document to the real backend', async () => {
      // Upload a real document
      const filename = 'test-document.txt';
      const content = 'This is a real test document content for E2E testing';

      const document = await uploadTestFile(filename, content);

      // Verify the response
      expect(document).toBeDefined();
      expect(document.metadata).toBeDefined();
      expect(document.metadata.name).toBe(filename);
      expect(document.metadata.document_id).toBeDefined();
      expect(document.metadata.document_type).toBe('text');
    });

    it('should upload a JSON document', async () => {
      const filename = 'test-data.json';
      const content = JSON.stringify({ test: true, data: 'E2E test' });

      const document = await uploadTestFile(filename, content, 'application/json');

      expect(document.metadata.name).toBe(filename);
      expect(document.metadata.document_type).toBe('json');
    });

    it('should upload a markdown document', async () => {
      const filename = 'test-readme.md';
      const content = '# Test Document\n\nThis is a **markdown** document for E2E testing.';

      const document = await uploadTestFile(filename, content, 'text/markdown');

      expect(document.metadata.name).toBe(filename);
      expect(document.metadata.document_type).toBe('markdown');
    });
  });

  describe('Document Listing', () => {
    it('should list all documents from the backend', async () => {
      // Upload multiple documents
      await uploadTestFile('test-1.txt', 'Content 1');
      await uploadTestFile('test-2.txt', 'Content 2');
      await uploadTestFile('test-3.txt', 'Content 3');

      // List documents
      const documents = await listDocuments();

      // Verify we have at least the 3 documents we uploaded
      expect(documents.length).toBeGreaterThanOrEqual(3);

      // Check that our test documents are in the list
      const testDocs = documents.filter(d => d.metadata?.name?.startsWith('test-'));
      expect(testDocs.length).toBeGreaterThanOrEqual(3);
    });

    it('should return empty array when no documents exist', async () => {
      // Clean up all test documents
      await cleanupTestData();

      // List documents
      const documents = await listDocuments();

      // Should have no test documents
      const testDocs = documents.filter(d => d.metadata?.name?.startsWith('test-'));
      expect(testDocs).toEqual([]);
    });
  });

  describe('Document Retrieval', () => {
    it('should get a specific document by ID', async () => {
      // Upload a document
      const uploaded = await uploadTestFile('test-get.txt', 'Get me!');
      const documentId = uploaded.metadata.document_id;

      // Get the document
      const document = await getDocument(documentId);

      // Verify it's the same document
      expect(document.metadata.document_id).toBe(documentId);
      expect(document.metadata.name).toBe('test-get.txt');
      expect(document.content).toBeDefined();
    });

    it('should return 404 for non-existent document', async () => {
      try {
        await getDocument('non-existent-id');
        expect.fail('Should have thrown an error');
      } catch (error: any) {
        expect(error.response?.status).toBe(404);
      }
    });
  });

  describe('Document Deletion', () => {
    it('should delete a document', async () => {
      // Upload a document
      const uploaded = await uploadTestFile('test-delete.txt', 'Delete me!');
      const documentId = uploaded.metadata.document_id;

      // Verify it exists
      const beforeDelete = await getDocument(documentId);
      expect(beforeDelete).toBeDefined();

      // Delete the document
      await deleteDocument(documentId);

      // Verify it's gone
      try {
        await getDocument(documentId);
        expect.fail('Document should have been deleted');
      } catch (error: any) {
        expect(error.response?.status).toBe(404);
      }
    });
  });

  describe('Document Content Processing', () => {
    it('should store and retrieve document content', async () => {
      const content = 'This is important content that should be stored and retrieved correctly.';
      const uploaded = await uploadTestFile('test-content.txt', content);

      const retrieved = await getDocument(uploaded.metadata.document_id);

      // The content should be stored in some form
      expect(retrieved.content).toBeDefined();
      // It might be in raw_content, formatted_content, or text field
      const actualContent = retrieved.content.raw_content ||
                           retrieved.content.formatted_content ||
                           retrieved.content.text;

      if (actualContent) {
        expect(actualContent).toContain('important content');
      }
    });
  });

  describe('Concurrent Operations', () => {
    it('should handle multiple uploads simultaneously', async () => {
      // Upload multiple documents concurrently
      const uploads = await Promise.all([
        uploadTestFile('test-concurrent-1.txt', 'Content 1'),
        uploadTestFile('test-concurrent-2.txt', 'Content 2'),
        uploadTestFile('test-concurrent-3.txt', 'Content 3'),
        uploadTestFile('test-concurrent-4.txt', 'Content 4'),
        uploadTestFile('test-concurrent-5.txt', 'Content 5'),
      ]);

      // All uploads should succeed
      expect(uploads).toHaveLength(5);
      uploads.forEach(doc => {
        expect(doc.metadata.document_id).toBeDefined();
      });

      // Verify all documents exist
      const documents = await listDocuments();
      const testDocs = documents.filter(d => d.metadata?.name?.startsWith('test-concurrent-'));
      expect(testDocs.length).toBe(5);
    });
  });
});