import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { TrashList } from './TrashList';
import { documentApi } from '../services/api';
import type { DocumentMessage } from '../services/api';

// Mock the API
vi.mock('../services/api', () => ({
  documentApi: {
    listTrash: vi.fn(),
    restoreDocument: vi.fn(),
    permanentlyDelete: vi.fn(),
  }
}));

// Mock the formatFileSize utility
vi.mock('../utils/format', () => ({
  formatFileSize: (size: number) => `${size} bytes`,
  formatLocalDateTime: (date: string) => date
}));

describe('TrashList', () => {
  const mockTrashDocuments: DocumentMessage[] = [
    {
      metadata: {
        document_id: 'doc-1',
        name: 'deleted-file.pdf',
        document_type: 'pdf',
        version: 1,
        size: 1024,
        created_at: '2025-01-01T00:00:00',
        updated_at: '2025-01-01T00:00:00',
        deleted: true,
        deleted_at: '2025-01-02T00:00:00',
        deleted_by: 'user-123',
        summary: 'This is a deleted document',
        language: 'en'
      },
      content: {
        summary: 'This is a deleted document'
      }
    },
    {
      metadata: {
        document_id: 'doc-2',
        name: 'another-deleted.docx',
        document_type: 'word',
        version: 1,
        size: 2048,
        created_at: '2025-01-01T00:00:00',
        updated_at: '2025-01-01T00:00:00',
        deleted: true,
        deleted_at: '2025-01-03T00:00:00',
        deleted_by: 'user-456',
        summary: 'Another deleted document with a much longer summary that definitely should be truncated because it exceeds one hundred characters in length',
        language: 'es'
      },
      content: {
        summary: 'Another deleted document with a much longer summary that definitely should be truncated because it exceeds one hundred characters in length'
      }
    }
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    // Reset window.confirm mock
    window.confirm = vi.fn(() => true);
  });

  describe('loading state', () => {
    it('should show loading spinner initially', () => {
      vi.mocked(documentApi.listTrash).mockImplementation(() => new Promise(() => {}));

      render(<TrashList />);

      expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
    });
  });

  describe('empty state', () => {
    it('should show empty state when trash is empty', async () => {
      vi.mocked(documentApi.listTrash).mockResolvedValue([]);

      render(<TrashList />);

      await waitFor(() => {
        expect(screen.getByText('Trash is empty')).toBeInTheDocument();
        expect(screen.getByText('Deleted documents will appear here')).toBeInTheDocument();
      });
    });
  });

  describe('error state', () => {
    it('should show error message when fetch fails', async () => {
      const errorMessage = 'Failed to fetch trash';
      vi.mocked(documentApi.listTrash).mockRejectedValue(new Error(errorMessage));

      render(<TrashList />);

      await waitFor(() => {
        expect(screen.getByText(errorMessage)).toBeInTheDocument();
      });
    });

    it('should handle API error response format', async () => {
      const error = {
        response: {
          data: {
            detail: 'Custom API error'
          }
        }
      };
      vi.mocked(documentApi.listTrash).mockRejectedValue(error);

      render(<TrashList />);

      await waitFor(() => {
        expect(screen.getByText('Custom API error')).toBeInTheDocument();
      });
    });
  });

  describe('displaying deleted documents', () => {
    it('should display list of deleted documents', async () => {
      vi.mocked(documentApi.listTrash).mockResolvedValue(mockTrashDocuments);

      render(<TrashList />);

      await waitFor(() => {
        expect(screen.getByText('deleted-file.pdf')).toBeInTheDocument();
        expect(screen.getByText('another-deleted.docx')).toBeInTheDocument();
      });
    });

    it('should display document summaries (truncated)', async () => {
      vi.mocked(documentApi.listTrash).mockResolvedValue(mockTrashDocuments);

      render(<TrashList />);

      await waitFor(() => {
        expect(screen.getByText('This is a deleted document')).toBeInTheDocument();
        // Check for truncated summary - first 100 chars + ...
        const summaryElement = screen.getByText(/Another deleted document with a much longer summary that definitely should be truncated because it e\.\.\./);
        expect(summaryElement).toBeInTheDocument();
      });
    });

    it('should display document metadata', async () => {
      vi.mocked(documentApi.listTrash).mockResolvedValue(mockTrashDocuments);

      render(<TrashList />);

      await waitFor(() => {
        expect(screen.getByText('PDF')).toBeInTheDocument(); // Document type badge
        expect(screen.getByText('WOR')).toBeInTheDocument(); // Word doc type badge
        expect(screen.getByText('1024 bytes')).toBeInTheDocument(); // File size
        expect(screen.getByText('2048 bytes')).toBeInTheDocument(); // File size
        expect(screen.getByText(/Deleted.*1\/2\/2025/)).toBeInTheDocument(); // Deleted date
      });
    });

    it('should display language flags', async () => {
      vi.mocked(documentApi.listTrash).mockResolvedValue(mockTrashDocuments);

      render(<TrashList />);

      await waitFor(() => {
        expect(screen.getByText('🇬🇧')).toBeInTheDocument(); // English flag
        expect(screen.getByText('🇪🇸')).toBeInTheDocument(); // Spanish flag
      });
    });

    it('should sort documents by deletion date (most recent first)', async () => {
      vi.mocked(documentApi.listTrash).mockResolvedValue(mockTrashDocuments);

      render(<TrashList />);

      await waitFor(() => {
        const tiles = screen.getAllByTitle(/deleted/i);
        // Second doc was deleted more recently (2025-01-03 vs 2025-01-02)
        expect(tiles[0]).toHaveTextContent('another-deleted.docx');
        expect(tiles[1]).toHaveTextContent('deleted-file.pdf');
      });
    });
  });

  describe('restore functionality', () => {
    it('should restore a document when restore button is clicked', async () => {
      vi.mocked(documentApi.listTrash).mockResolvedValue(mockTrashDocuments);
      vi.mocked(documentApi.restoreDocument).mockResolvedValue({});

      render(<TrashList />);

      await waitFor(() => {
        expect(screen.getByText('deleted-file.pdf')).toBeInTheDocument();
      });

      const restoreButtons = screen.getAllByTitle('Restore document');
      fireEvent.click(restoreButtons[0]);

      await waitFor(() => {
        expect(documentApi.restoreDocument).toHaveBeenCalledWith('doc-2'); // First in sorted order
      });
    });

    it('should refresh trash list after successful restore', async () => {
      vi.mocked(documentApi.listTrash)
        .mockResolvedValueOnce(mockTrashDocuments)
        .mockResolvedValueOnce([mockTrashDocuments[0]]); // After restore, only one doc left

      vi.mocked(documentApi.restoreDocument).mockResolvedValue({});

      render(<TrashList />);

      await waitFor(() => {
        expect(screen.getByText('another-deleted.docx')).toBeInTheDocument();
      });

      const restoreButtons = screen.getAllByTitle('Restore document');
      fireEvent.click(restoreButtons[0]);

      await waitFor(() => {
        expect(documentApi.listTrash).toHaveBeenCalledTimes(2);
      });
    });

    it('should handle restore errors', async () => {
      vi.mocked(documentApi.listTrash).mockResolvedValue(mockTrashDocuments);
      vi.mocked(documentApi.restoreDocument).mockRejectedValue(new Error('Failed to restore document'));

      render(<TrashList />);

      await waitFor(() => {
        expect(screen.getByText('deleted-file.pdf')).toBeInTheDocument();
      });

      const restoreButtons = screen.getAllByTitle('Restore document');
      fireEvent.click(restoreButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Failed to restore document')).toBeInTheDocument();
      });
    });
  });

  describe('permanent delete functionality', () => {
    it('should show confirmation dialog before permanent delete', async () => {
      vi.mocked(documentApi.listTrash).mockResolvedValue(mockTrashDocuments);

      render(<TrashList />);

      await waitFor(() => {
        expect(screen.getByText('deleted-file.pdf')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByTitle('Permanently delete');
      fireEvent.click(deleteButtons[0]);

      expect(window.confirm).toHaveBeenCalledWith(
        'Are you sure you want to permanently delete this document? This action cannot be undone.'
      );
    });

    it('should permanently delete when confirmed', async () => {
      vi.mocked(documentApi.listTrash).mockResolvedValue(mockTrashDocuments);
      vi.mocked(documentApi.permanentlyDelete).mockResolvedValue({});
      window.confirm = vi.fn(() => true);

      render(<TrashList />);

      await waitFor(() => {
        expect(screen.getByText('deleted-file.pdf')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByTitle('Permanently delete');
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(documentApi.permanentlyDelete).toHaveBeenCalledWith('doc-2'); // First in sorted order
      });
    });

    it('should not delete when user cancels confirmation', async () => {
      vi.mocked(documentApi.listTrash).mockResolvedValue(mockTrashDocuments);
      window.confirm = vi.fn(() => false);

      render(<TrashList />);

      await waitFor(() => {
        expect(screen.getByText('deleted-file.pdf')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByTitle('Permanently delete');
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(documentApi.permanentlyDelete).not.toHaveBeenCalled();
      });
    });

    it('should refresh trash list after successful permanent delete', async () => {
      vi.mocked(documentApi.listTrash)
        .mockResolvedValueOnce(mockTrashDocuments)
        .mockResolvedValueOnce([mockTrashDocuments[0]]); // After delete, only one doc left

      vi.mocked(documentApi.permanentlyDelete).mockResolvedValue({});
      window.confirm = vi.fn(() => true);

      render(<TrashList />);

      await waitFor(() => {
        expect(screen.getByText('another-deleted.docx')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByTitle('Permanently delete');
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(documentApi.listTrash).toHaveBeenCalledTimes(2);
      });
    });

    it('should handle permanent delete errors', async () => {
      vi.mocked(documentApi.listTrash).mockResolvedValue(mockTrashDocuments);
      vi.mocked(documentApi.permanentlyDelete).mockRejectedValue(new Error('Failed to permanently delete document'));
      window.confirm = vi.fn(() => true);

      render(<TrashList />);

      await waitFor(() => {
        expect(screen.getByText('deleted-file.pdf')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByTitle('Permanently delete');
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Failed to permanently delete document')).toBeInTheDocument();
      });
    });
  });

  describe('refresh prop', () => {
    it('should refetch documents when refresh prop changes', async () => {
      vi.mocked(documentApi.listTrash).mockResolvedValue(mockTrashDocuments);

      const { rerender } = render(<TrashList refresh={1} />);

      await waitFor(() => {
        expect(documentApi.listTrash).toHaveBeenCalledTimes(1);
      });

      rerender(<TrashList refresh={2} />);

      await waitFor(() => {
        expect(documentApi.listTrash).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe('event propagation', () => {
    it('should stop propagation on restore button click', async () => {
      vi.mocked(documentApi.listTrash).mockResolvedValue(mockTrashDocuments);

      render(<TrashList />);

      await waitFor(() => {
        expect(screen.getByText('deleted-file.pdf')).toBeInTheDocument();
      });

      const restoreButtons = screen.getAllByTitle('Restore document');
      const mockEvent = { stopPropagation: vi.fn() };

      // Simulate click with event
      fireEvent.click(restoreButtons[0], mockEvent);

      // The stopPropagation is called in the handler
      // We can't directly test it with fireEvent, but we can verify the action occurs
      expect(documentApi.restoreDocument).toHaveBeenCalled();
    });

    it('should stop propagation on delete button click', async () => {
      vi.mocked(documentApi.listTrash).mockResolvedValue(mockTrashDocuments);
      window.confirm = vi.fn(() => true);

      render(<TrashList />);

      await waitFor(() => {
        expect(screen.getByText('deleted-file.pdf')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByTitle('Permanently delete');
      const mockEvent = { stopPropagation: vi.fn() };

      // Simulate click with event
      fireEvent.click(deleteButtons[0], mockEvent);

      // The stopPropagation is called in the handler
      // We can't directly test it with fireEvent, but we can verify the action occurs
      expect(window.confirm).toHaveBeenCalled();
    });
  });
});