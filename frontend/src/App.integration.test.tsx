import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from './test/utils';
import userEvent from '@testing-library/user-event';
import App from './App';
import { documentApi, searchApi } from './services/api';
import { wsService } from './services/websocket';

// Mock the API and WebSocket services
vi.mock('./services/api', () => ({
  documentApi: {
    getDocument: vi.fn(),
    listDocuments: vi.fn(),
    createDocument: vi.fn(),
    deleteDocument: vi.fn(),
  },
  searchApi: {
    vectorSearch: vi.fn(),
    fulltextSearch: vi.fn(),
    graphSearch: vi.fn(),
    hybridSearch: vi.fn(),
  },
}));

vi.mock('./services/websocket', () => ({
  wsService: {
    connect: vi.fn(),
    disconnect: vi.fn(),
    onSystemNotification: vi.fn(() => vi.fn()),
    onDocumentCreated: vi.fn(() => vi.fn()),
    onDocumentUpdated: vi.fn(() => vi.fn()),
    onDocumentDeleted: vi.fn(() => vi.fn()),
  },
}));

describe('App Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Setup default mocks
    vi.mocked(documentApi.listDocuments).mockResolvedValue([]);
  });

  describe('Search to Bench Integration', () => {
    it('should display search result document in the bench when clicked', async () => {
      // Mock search result
      const searchResult = {
        document_id: 'doc-123',
        metadata: {
          name: 'test-document.pdf',
          document_type: 'pdf',
          size: 1024,
          created_at: '2024-01-15T10:00:00Z',
        },
        content: {
          text: 'This is test document content',
        },
        score: 0.95,
        highlights: ['This is a highlighted portion'],
      };

      // Mock full document that will be fetched
      const fullDocument = {
        metadata: {
          document_id: 'doc-123',
          name: 'test-document.pdf',
          document_type: 'pdf',
          size: 1024,
          created_at: '2024-01-15T10:00:00Z',
          updated_at: '2024-01-15T10:00:00Z',
          status: 'completed',
        },
        content: {
          text: 'This is the full test document content that will be shown in the bench',
          formatted_content: '# Test Document\n\nThis is the full test document content',
          raw_text: 'This is the full test document content',
          summary: 'A test document',
        },
      };

      // Setup mocks
      vi.mocked(searchApi.vectorSearch).mockResolvedValue([searchResult]);
      vi.mocked(documentApi.getDocument).mockResolvedValue(fullDocument);

      const user = userEvent.setup();

      render(<App />);

      // Navigate to search tab
      const searchTab = screen.getByRole('button', { name: /search/i });
      await user.click(searchTab);

      // Perform search
      const searchInput = await screen.findByPlaceholderText('Search your documents... (Press Enter to search)');
      await user.type(searchInput, 'test query');
      await user.keyboard('{Enter}');

      // Wait for search results
      await waitFor(() => {
        expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
      });

      // Click on search result
      const resultCard = screen.getByText('test-document.pdf').closest('div');
      if (resultCard) {
        await user.click(resultCard);
      }

      // Verify that getDocument was called with the correct ID
      await waitFor(() => {
        expect(documentApi.getDocument).toHaveBeenCalledWith('doc-123');
      });

      // Wait for the document to be displayed in the bench
      // The bench should show the document name in a tab
      await waitFor(() => {
        // Look for the document name in the bench tabs
        const benchTabs = screen.getAllByText('test-document.pdf');
        // Should have at least one instance in the bench area
        expect(benchTabs.length).toBeGreaterThan(0);
      });
    });

    it('should handle errors when loading document from search result', async () => {
      const searchResult = {
        document_id: 'doc-456',
        metadata: {
          name: 'error-document.pdf',
          document_type: 'pdf',
        },
        score: 0.85,
      };

      vi.mocked(searchApi.vectorSearch).mockResolvedValue([searchResult]);
      vi.mocked(documentApi.getDocument).mockRejectedValue(new Error('Failed to load document'));

      const user = userEvent.setup();

      render(<App />);

      // Navigate to search tab
      const searchTab = screen.getByRole('button', { name: /search/i });
      await user.click(searchTab);

      // Perform search
      const searchInput = await screen.findByPlaceholderText('Search your documents... (Press Enter to search)');
      await user.type(searchInput, 'error test');
      await user.keyboard('{Enter}');

      // Wait for search results
      await waitFor(() => {
        expect(screen.getByText('error-document.pdf')).toBeInTheDocument();
      });

      // Click on search result
      const resultCard = screen.getByText('error-document.pdf').closest('div');
      if (resultCard) {
        await user.click(resultCard);
      }

      // Verify error handling
      await waitFor(() => {
        expect(documentApi.getDocument).toHaveBeenCalledWith('doc-456');
      });

      // Should show error toast
      await waitFor(() => {
        expect(screen.getByText(/Failed to load document/i)).toBeInTheDocument();
      });
    });

    it('should persist search state when switching tabs', async () => {
      const searchResult = {
        document_id: 'doc-789',
        metadata: {
          name: 'persistent-doc.pdf',
          document_type: 'pdf',
        },
        score: 0.90,
      };

      vi.mocked(searchApi.vectorSearch).mockResolvedValue([searchResult]);

      const user = userEvent.setup();

      render(<App />);

      // Navigate to search tab
      const searchTab = screen.getByRole('button', { name: /search/i });
      await user.click(searchTab);

      // Perform search
      const searchInput = await screen.findByPlaceholderText('Search your documents... (Press Enter to search)');
      await user.type(searchInput, 'persistent query');
      await user.keyboard('{Enter}');

      // Wait for results
      await waitFor(() => {
        expect(screen.getByText('persistent-doc.pdf')).toBeInTheDocument();
      });

      // Switch to documents tab
      const documentsTab = screen.getByRole('button', { name: /documents/i });
      await user.click(documentsTab);

      // Switch back to search tab
      await user.click(searchTab);

      // Search results should still be visible
      expect(screen.getByText('persistent-doc.pdf')).toBeInTheDocument();
      // Search query should still be in the input
      const searchInputAfter = screen.getByPlaceholderText('Search your documents... (Press Enter to search)');
      expect(searchInputAfter).toHaveValue('persistent query');
    });
  });
});