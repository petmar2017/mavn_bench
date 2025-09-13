import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '../test/utils';
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

    render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

    // Should show skeletons while loading
    expect(screen.getByTestId('skeleton')).toBeInTheDocument();
  });

  it('should render documents in a table', async () => {
    vi.mocked(documentApi.listDocuments).mockResolvedValueOnce(mockDocuments);

    render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

    await waitFor(() => {
      expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
      expect(screen.getByText('another-document.docx')).toBeInTheDocument();
      expect(screen.getByText('presentation.pptx')).toBeInTheDocument();
    });

    // Check table headers
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Type')).toBeInTheDocument();
    expect(screen.getByText('Size')).toBeInTheDocument();
    expect(screen.getByText('Status')).toBeInTheDocument();
    expect(screen.getByText('Modified')).toBeInTheDocument();
  });

  it('should show empty state when no documents', async () => {
    vi.mocked(documentApi.listDocuments).mockResolvedValueOnce([]);

    render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

    await waitFor(() => {
      expect(screen.getByText(/no documents yet/i)).toBeInTheDocument();
      expect(screen.getByText(/upload your first document/i)).toBeInTheDocument();
    });
  });

  it('should handle document selection on row click', async () => {
    vi.mocked(documentApi.listDocuments).mockResolvedValueOnce(mockDocuments);

    render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

    await waitFor(() => {
      expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
    });

    const firstRow = screen.getByText('test-document.pdf').closest('tr')!;
    fireEvent.click(firstRow);

    expect(mockOnDocumentSelect).toHaveBeenCalledWith(mockDocuments[0]);
  });

  it('should show document status badges', async () => {
    vi.mocked(documentApi.listDocuments).mockResolvedValueOnce(mockDocuments);

    render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

    await waitFor(() => {
      expect(screen.getByText('completed')).toBeInTheDocument();
      expect(screen.getByText('processing')).toBeInTheDocument();
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
          size: 1048576, // 1 MB
        },
      },
      {
        ...mockDocument,
        metadata: {
          ...mockDocument.metadata,
          document_id: 'doc-3',
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

    render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

    await waitFor(() => {
      expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
    });

    // Open the menu for the first document
    const menuButtons = screen.getAllByRole('button');
    const firstMenuButton = menuButtons.find(btn => btn.querySelector('svg')); // Find button with icon

    if (firstMenuButton) {
      await user.click(firstMenuButton);

      // Click delete option
      const deleteOption = await screen.findByText('Delete');
      await user.click(deleteOption);

      expect(documentApi.deleteDocument).toHaveBeenCalledWith('doc-123');
    }
  });

  it('should handle delete errors gracefully', async () => {
    vi.mocked(documentApi.listDocuments).mockResolvedValueOnce(mockDocuments);
    vi.mocked(documentApi.deleteDocument).mockRejectedValueOnce(
      { response: { data: { detail: 'Delete failed' } } }
    );

    const user = userEvent.setup();

    render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

    await waitFor(() => {
      expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
    });

    // Open menu and click delete
    const menuButtons = screen.getAllByRole('button');
    const firstMenuButton = menuButtons.find(btn => btn.querySelector('svg'));

    if (firstMenuButton) {
      await user.click(firstMenuButton);
      const deleteOption = await screen.findByText('Delete');
      await user.click(deleteOption);

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

    if (notificationCallback) {
      notificationCallback({ type: 'document_created', data: mockDocument });
    }

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

  it('should show document type badges', async () => {
    vi.mocked(documentApi.listDocuments).mockResolvedValueOnce(mockDocuments);

    render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

    await waitFor(() => {
      expect(screen.getByText('pdf')).toBeInTheDocument();
      expect(screen.getByText('word')).toBeInTheDocument();
      expect(screen.getByText('powerpoint')).toBeInTheDocument();
    });
  });

  it('should format dates correctly', async () => {
    const testDate = '2024-01-15T10:30:00Z';
    vi.mocked(documentApi.listDocuments).mockResolvedValueOnce([
      {
        ...mockDocument,
        metadata: {
          ...mockDocument.metadata,
          updated_at: testDate,
        },
      },
    ]);

    render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

    await waitFor(() => {
      // Check if date is formatted (exact format may vary based on locale)
      const dateElements = screen.getAllByText(/Jan|15|2024/);
      expect(dateElements.length).toBeGreaterThan(0);
    });
  });

  it('should handle view action from menu', async () => {
    vi.mocked(documentApi.listDocuments).mockResolvedValueOnce(mockDocuments);

    const user = userEvent.setup();

    render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

    await waitFor(() => {
      expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
    });

    // Open menu
    const menuButtons = screen.getAllByRole('button');
    const firstMenuButton = menuButtons.find(btn => btn.querySelector('svg'));

    if (firstMenuButton) {
      await user.click(firstMenuButton);

      // Click view option
      const viewOption = await screen.findByText('View');
      await user.click(viewOption);

      expect(mockOnDocumentSelect).toHaveBeenCalledWith(mockDocuments[0]);
    }
  });

  it('should stop event propagation on menu button click', async () => {
    vi.mocked(documentApi.listDocuments).mockResolvedValueOnce(mockDocuments);

    const user = userEvent.setup();

    render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

    await waitFor(() => {
      expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
    });

    // Click menu button (should not trigger row selection)
    const menuButtons = screen.getAllByRole('button');
    const firstMenuButton = menuButtons.find(btn => btn.querySelector('svg'));

    if (firstMenuButton) {
      await user.click(firstMenuButton);

      // onDocumentSelect should not be called from menu button click
      expect(mockOnDocumentSelect).not.toHaveBeenCalled();
    }
  });
});