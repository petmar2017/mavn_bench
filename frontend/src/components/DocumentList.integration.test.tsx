import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '../test/utils';
import { DocumentList } from './DocumentList';
import { documentApi } from '../services/api';

// Mock only the API, not the component
vi.mock('../services/api', () => ({
  documentApi: {
    listDocuments: vi.fn(),
    deleteDocument: vi.fn(),
  },
}));

vi.mock('../services/websocket', () => ({
  wsService: {
    onSystemNotification: vi.fn(() => vi.fn()),
  },
}));

describe('DocumentList Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should handle real API response structure correctly', async () => {
    // This mimics the actual backend response structure
    const realApiResponse = {
      documents: [
        {
          metadata: {
            document_id: 'doc-1',
            name: 'test.pdf',
            document_type: 'pdf',
            size: 1024,
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z',
            status: 'completed',
          },
          content: {
            text: 'Test content',
            summary: 'Test summary',
          },
        },
      ],
      total: 1,
      limit: 10,
      offset: 0,
    };

    // Mock the API to return the wrapped response
    vi.mocked(documentApi.listDocuments).mockResolvedValueOnce(
      realApiResponse.documents
    );

    render(<DocumentList onDocumentSelect={vi.fn()} />);

    // Wait for the documents to load
    await waitFor(() => {
      expect(screen.getByText('test.pdf')).toBeInTheDocument();
    });

    // Verify the table renders correctly
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Type')).toBeInTheDocument();
    expect(screen.getByText('Size')).toBeInTheDocument();
    expect(screen.getByText('Status')).toBeInTheDocument();
  });

  it('should handle empty documents array from API', async () => {
    // Test with empty response
    vi.mocked(documentApi.listDocuments).mockResolvedValueOnce([]);

    render(<DocumentList onDocumentSelect={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText(/no documents yet/i)).toBeInTheDocument();
    });
  });

  it('should handle API errors gracefully', async () => {
    // Test error handling
    vi.mocked(documentApi.listDocuments).mockRejectedValueOnce(
      new Error('Network error')
    );

    render(<DocumentList onDocumentSelect={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText(/failed to fetch documents/i)).toBeInTheDocument();
    });
  });

  it('should handle malformed API responses', async () => {
    // Test with non-array response (should be handled by the component)
    vi.mocked(documentApi.listDocuments).mockResolvedValueOnce(null as any);

    render(<DocumentList onDocumentSelect={vi.fn()} />);

    await waitFor(() => {
      // Component should handle null and show empty state
      expect(screen.getByText(/no documents yet/i)).toBeInTheDocument();
    });
  });

  it('should handle documents with missing required fields', async () => {
    const incompleteDocument = {
      metadata: {
        document_id: 'doc-1',
        name: undefined, // Missing name
        document_type: 'pdf',
      },
      content: {},
    };

    vi.mocked(documentApi.listDocuments).mockResolvedValueOnce([incompleteDocument as any]);

    render(<DocumentList onDocumentSelect={vi.fn()} />);

    await waitFor(() => {
      // Should handle missing fields gracefully
      const table = screen.getByRole('table');
      expect(table).toBeInTheDocument();
    });
  });
});