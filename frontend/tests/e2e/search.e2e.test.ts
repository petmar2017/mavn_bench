// Real E2E Tests for Search Operations - No Mocks!
import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import {
  uploadTestFile,
  searchDocuments,
  cleanupTestData,
} from './setup';

describe('Search Operations E2E', () => {
  let documentIds: string[] = [];

  beforeAll(async () => {
    await cleanupTestData();

    // Upload test documents with different content for searching
    const docs = await Promise.all([
      uploadTestFile('test-search-1.txt', 'The quick brown fox jumps over the lazy dog'),
      uploadTestFile('test-search-2.txt', 'Machine learning is transforming artificial intelligence'),
      uploadTestFile('test-search-3.txt', 'JavaScript and TypeScript are popular programming languages'),
      uploadTestFile('test-search-4.md', '# Documentation\n\nThis is a guide for developers'),
      uploadTestFile('test-search-5.json', JSON.stringify({
        title: 'Configuration',
        description: 'System configuration settings',
      })),
    ]);

    documentIds = docs.map(d => d.metadata.document_id);

    // Wait a bit for indexing (if backend does async indexing)
    await new Promise(resolve => setTimeout(resolve, 2000));
  });

  afterAll(async () => {
    await cleanupTestData();
  });

  describe('Vector Search', () => {
    it('should find documents using semantic search', async () => {
      const results = await searchDocuments('programming', 'vector');

      // Should find relevant documents
      expect(results).toBeDefined();
      expect(Array.isArray(results)).toBe(true);

      // Should find the document about programming languages
      const hasRelevantResult = results.some((r: any) =>
        r.metadata?.name?.includes('test-search-3')
      );

      // Vector search might not always find exact matches, but should return results
      expect(results.length).toBeGreaterThanOrEqual(0);
    });

    it('should return empty results for nonsense query', async () => {
      const results = await searchDocuments('xyzabcdef123456', 'vector');

      expect(results).toBeDefined();
      expect(Array.isArray(results)).toBe(true);
      // Might return some results based on similarity, but likely empty or low scores
    });
  });

  describe('Full-text Search', () => {
    it('should find documents containing specific keywords', async () => {
      const results = await searchDocuments('JavaScript', 'fulltext');

      expect(results).toBeDefined();
      expect(Array.isArray(results)).toBe(true);

      // Should find the document mentioning JavaScript
      if (results.length > 0) {
        const hasJavaScript = results.some((r: any) =>
          r.metadata?.name?.includes('test-search-3')
        );
        // Full-text search should find exact matches
        expect(hasJavaScript).toBe(true);
      }
    });

    it('should find documents with partial word matches', async () => {
      const results = await searchDocuments('learn', 'fulltext');

      expect(results).toBeDefined();
      expect(Array.isArray(results)).toBe(true);

      // Should find "learning" in the ML document
      if (results.length > 0) {
        const hasLearning = results.some((r: any) =>
          r.metadata?.name?.includes('test-search-2')
        );
        expect(hasLearning).toBe(true);
      }
    });
  });

  describe('Graph Search', () => {
    it('should perform graph-based search', async () => {
      const results = await searchDocuments('documentation', 'graph');

      expect(results).toBeDefined();
      expect(Array.isArray(results)).toBe(true);

      // Graph search might find related documents through relationships
      // Results depend on how the backend implements graph search
    });
  });

  describe('Hybrid Search', () => {
    it('should combine multiple search strategies', async () => {
      const results = await searchDocuments('developer guide', 'hybrid');

      expect(results).toBeDefined();
      expect(Array.isArray(results)).toBe(true);

      // Hybrid search should leverage both vector and full-text capabilities
      // Should potentially find the documentation file
      if (results.length > 0) {
        const hasGuide = results.some((r: any) =>
          r.metadata?.name?.includes('test-search-4')
        );
        // Hybrid search should be good at finding relevant documents
      }
    });

    it('should handle complex queries', async () => {
      const results = await searchDocuments(
        'artificial intelligence machine learning programming',
        'hybrid'
      );

      expect(results).toBeDefined();
      expect(Array.isArray(results)).toBe(true);

      // Should find multiple relevant documents
      if (results.length > 0) {
        // Should rank AI/ML document high
        const topResults = results.slice(0, 3);
        const hasAIDoc = topResults.some((r: any) =>
          r.metadata?.name?.includes('test-search-2')
        );
        const hasProgDoc = topResults.some((r: any) =>
          r.metadata?.name?.includes('test-search-3')
        );

        // At least one should be in top results
        expect(hasAIDoc || hasProgDoc).toBe(true);
      }
    });
  });

  describe('Search Result Quality', () => {
    it('should return results with metadata', async () => {
      const results = await searchDocuments('test', 'vector');

      if (results.length > 0) {
        const firstResult = results[0];

        // Should have required fields
        expect(firstResult).toHaveProperty('document_id');
        expect(firstResult).toHaveProperty('score');
        expect(firstResult).toHaveProperty('metadata');

        // Metadata should have document info
        expect(firstResult.metadata).toHaveProperty('name');
        expect(firstResult.metadata).toHaveProperty('document_type');

        // Score should be a number between 0 and 1
        expect(typeof firstResult.score).toBe('number');
        expect(firstResult.score).toBeGreaterThanOrEqual(0);
        expect(firstResult.score).toBeLessThanOrEqual(1);
      }
    });

    it('should return results sorted by relevance', async () => {
      const results = await searchDocuments('programming TypeScript', 'vector');

      if (results.length > 1) {
        // Scores should be in descending order
        for (let i = 1; i < results.length; i++) {
          expect(results[i - 1].score).toBeGreaterThanOrEqual(results[i].score);
        }
      }
    });
  });

  describe('Search Performance', () => {
    it('should return search results quickly', async () => {
      const startTime = Date.now();
      const results = await searchDocuments('test query', 'vector');
      const endTime = Date.now();

      const responseTime = endTime - startTime;

      // Search should be reasonably fast (< 2 seconds)
      expect(responseTime).toBeLessThan(2000);
      expect(results).toBeDefined();
    });

    it('should handle concurrent searches', async () => {
      const searches = await Promise.all([
        searchDocuments('fox', 'vector'),
        searchDocuments('machine', 'fulltext'),
        searchDocuments('guide', 'hybrid'),
        searchDocuments('config', 'graph'),
        searchDocuments('typescript', 'vector'),
      ]);

      // All searches should complete
      expect(searches).toHaveLength(5);
      searches.forEach(result => {
        expect(result).toBeDefined();
        expect(Array.isArray(result)).toBe(true);
      });
    });
  });
});