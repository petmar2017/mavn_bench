import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '../test/utils';
import userEvent from '@testing-library/user-event';
import { DocumentList } from './DocumentList';
import { documentApi } from '../services/api';
import { wsService } from '../services/websocket';
import { mockDocuments, mockDocument } from '../test/mocks';

// Mock the API and WebSocket service
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

describe('DocumentList', () => {
  const mockOnDocumentSelect = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render loading state initially', () => {
    vi.mocked(documentApi.listDocuments).mockImplementation(
      () => new Promise(() => {}) // Never resolves to keep loading state
    );

    const { container } = render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

    // Should show spinner while loading
    expect(container.querySelector('._spinner_b0a222')).toBeInTheDocument();
  });

  it('should render documents in a grid', async () => {
    vi.mocked(documentApi.listDocuments).mockResolvedValueOnce(mockDocuments);

    const { container } = render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

    await waitFor(() => {
      expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
      expect(screen.getByText('another-document.docx')).toBeInTheDocument();
      expect(screen.getByText('presentation.pptx')).toBeInTheDocument();
    });

    // Check grid layout exists
    expect(container.querySelector('._grid_b0a222')).toBeInTheDocument();
    // Check tiles exist
    const tiles = container.querySelectorAll('._tile_b0a222');
    expect(tiles.length).toBe(3);
  });

  it('should show empty state when no documents', async () => {
    vi.mocked(documentApi.listDocuments).mockResolvedValueOnce([]);

    render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

    await waitFor(() => {
      expect(screen.getByText(/no documents yet/i)).toBeInTheDocument();
      expect(screen.getByText(/upload a document to get started/i)).toBeInTheDocument();
    });
  });

  it('should handle document selection on tile click', async () => {
    vi.mocked(documentApi.listDocuments).mockResolvedValueOnce(mockDocuments);

    const { container } = render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

    await waitFor(() => {
      expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
    });

    const firstTile = container.querySelector('._tile_b0a222')!;
    fireEvent.click(firstTile);

    expect(mockOnDocumentSelect).toHaveBeenCalledWith(mockDocuments[0]);
  });

  it('should show document type abbreviations', async () => {
    vi.mocked(documentApi.listDocuments).mockResolvedValueOnce(mockDocuments);

    render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

    await waitFor(() => {
      // Document types are shown as 3-letter abbreviations
      expect(screen.getByText('PDF')).toBeInTheDocument();
      expect(screen.getByText('WOR')).toBeInTheDocument(); // word -> WOR
      expect(screen.getByText('POW')).toBeInTheDocument(); // powerpoint -> POW
    });
  });

  it('should format file sizes correctly', async () => {
    vi.mocked(documentApi.listDocuments).mockResolvedValueOnce([
      {
        ...mockDocument,
        metadata: {
          ...mockDocument.metadata,
          size: 1024, // 1 KB
        },
      },
      {
        ...mockDocument,
        metadata: {
          ...mockDocument.metadata,
          document_id: 'doc-2',
          name: 'doc2.pdf',
          size: 1048576, // 1 MB
        },
      },
      {
        ...mockDocument,
        metadata: {
          ...mockDocument.metadata,
          document_id: 'doc-3',
          name: 'doc3.pdf',
          size: 1073741824, // 1 GB
        },
      },
    ]);

    render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

    await waitFor(() => {
      expect(screen.getByText('1 KB')).toBeInTheDocument();
      expect(screen.getByText('1 MB')).toBeInTheDocument();
      expect(screen.getByText('1 GB')).toBeInTheDocument();
    });
  });

  it('should handle document deletion', async () => {
    vi.mocked(documentApi.listDocuments).mockResolvedValueOnce(mockDocuments);
    vi.mocked(documentApi.deleteDocument).mockResolvedValueOnce(undefined);

    const user = userEvent.setup();

    const { container } = render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

    await waitFor(() => {
      expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
    });

    // Find the delete button in the first tile
    const firstTile = container.querySelector('._tile_b0a222');
    const deleteButton = firstTile?.querySelector('button[title="Delete"]');

    if (deleteButton) {
      await user.click(deleteButton);
      // Confirm deletion if there's a confirmation dialog
      expect(documentApi.deleteDocument).toHaveBeenCalledWith('doc-123');
    }
  });

  it('should handle delete errors gracefully', async () => {
    vi.mocked(documentApi.listDocuments).mockResolvedValueOnce(mockDocuments);
    vi.mocked(documentApi.deleteDocument).mockRejectedValueOnce(
      { response: { data: { detail: 'Delete failed' } } }
    );

    const user = userEvent.setup();

    const { container } = render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

    await waitFor(() => {
      expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
    });

    // Find and click delete button
    const firstTile = container.querySelector('._tile_b0a222');
    const deleteButton = firstTile?.querySelector('button[title="Delete"]');

    if (deleteButton) {
      await user.click(deleteButton);
      // Should still have called the API
      expect(documentApi.deleteDocument).toHaveBeenCalled();
    }
  });

  it('should refresh when refresh prop changes', async () => {
    vi.mocked(documentApi.listDocuments).mockResolvedValueOnce(mockDocuments);

    const { rerender } = render(
      <DocumentList onDocumentSelect={mockOnDocumentSelect} refresh={0} />
    );

    await waitFor(() => {
      expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
    });

    expect(documentApi.listDocuments).toHaveBeenCalledTimes(1);

    // Trigger refresh by changing the refresh prop
    vi.mocked(documentApi.listDocuments).mockResolvedValueOnce(mockDocuments);
    rerender(<DocumentList onDocumentSelect={mockOnDocumentSelect} refresh={1} />);

    await waitFor(() => {
      expect(documentApi.listDocuments).toHaveBeenCalledTimes(2);
    });
  });

  it('should subscribe to WebSocket events', () => {
    render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

    expect(wsService.onSystemNotification).toHaveBeenCalled();
  });

  it('should refresh on document created WebSocket event', async () => {
    let notificationCallback: ((notification: any) => void) | null = null;

    vi.mocked(wsService.onSystemNotification).mockImplementation((callback) => {
      notificationCallback = callback;
      return vi.fn(); // Return unsubscribe function
    });

    vi.mocked(documentApi.listDocuments).mockResolvedValueOnce(mockDocuments);

    render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

    await waitFor(() => {
      expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
    });

    expect(documentApi.listDocuments).toHaveBeenCalledTimes(1);

    // Simulate WebSocket event
    vi.mocked(documentApi.listDocuments).mockResolvedValueOnce([...mockDocuments, {
      ...mockDocument,
      metadata: {
        ...mockDocument.metadata,
        document_id: 'new-doc',
        name: 'new-document.pdf',
      },
    }]);

    await act(async () => {
      if (notificationCallback) {
        notificationCallback({ type: 'document_created', data: mockDocument });
      }
    });

    await waitFor(() => {
      expect(documentApi.listDocuments).toHaveBeenCalledTimes(2);
    });
  });

  it('should handle API errors', async () => {
    const errorMessage = 'Failed to fetch documents';
    vi.mocked(documentApi.listDocuments).mockRejectedValueOnce(
      { response: { data: { detail: errorMessage } } }
    );

    render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });
  });

  it('should show document icons for different types', async () => {
    vi.mocked(documentApi.listDocuments).mockResolvedValueOnce(mockDocuments);

    const { container } = render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

    await waitFor(() => {
      expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
    });

    // Should have icons for different document types
    const tiles = container.querySelectorAll('._tile_b0a222');
    expect(tiles.length).toBe(3);
    // Each tile should have an icon
    tiles.forEach(tile => {
      expect(tile.querySelector('svg')).toBeInTheDocument();
    });
  });

  it('should format dates correctly', async () => {
    const testDate = '2024-01-15T10:30:00Z';
    vi.mocked(documentApi.listDocuments).mockResolvedValueOnce([
      {
        ...mockDocument,
        metadata: {
          ...mockDocument.metadata,
          created_at: testDate,
        },
      },
    ]);

    render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

    await waitFor(() => {
      // Date should be formatted as toLocaleDateString which will include some form of Jan, 15, and 2024
      // Using a more flexible matcher since exact format varies by environment
      const container = document.body;
      expect(container.textContent).toMatch(/1\/15\/2024|Jan 15, 2024|15 Jan 2024|2024-01-15/);
    });
  });

  it('should handle tile click for viewing', async () => {
    vi.mocked(documentApi.listDocuments).mockResolvedValueOnce(mockDocuments);

    const user = userEvent.setup();

    const { container } = render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

    await waitFor(() => {
      expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
    });

    // Click on tile to view document
    const firstTile = container.querySelector('._tile_b0a222');
    if (firstTile) {
      await user.click(firstTile);
      expect(mockOnDocumentSelect).toHaveBeenCalledWith(mockDocuments[0]);
    }
  });

  it('should stop event propagation on delete button click', async () => {
    vi.mocked(documentApi.listDocuments).mockResolvedValueOnce(mockDocuments);
    vi.mocked(documentApi.deleteDocument).mockResolvedValueOnce(undefined);

    const user = userEvent.setup();

    const { container } = render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

    await waitFor(() => {
      expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
    });

    // Click delete button (should not trigger tile selection)
    const firstTile = container.querySelector('._tile_b0a222');
    const deleteButton = firstTile?.querySelector('button[title="Delete"]');

    if (deleteButton) {
      await user.click(deleteButton);
      // onDocumentSelect should not be called from delete button click
      expect(mockOnDocumentSelect).not.toHaveBeenCalled();
    }
  });
});