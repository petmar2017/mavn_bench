import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { DocumentList } from './DocumentList';
import { documentApi } from '../services/api';
import { wsService } from '../services/websocket';
import type { DocumentMessage } from '../services/api';

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

// Mock the formatFileSize utility
vi.mock('../utils/format', () => ({
  formatFileSize: (size: number) => `${size} bytes`,
  formatLocalDateTime: (date: string) => date
}));

describe('DocumentList - Soft Delete Functionality', () => {
  const mockDocuments: DocumentMessage[] = [
    {
      metadata: {
        document_id: 'doc-1',
        name: 'test-file.pdf',
        document_type: 'pdf',
        version: 1,
        size: 1024,
        created_at: '2025-01-01T00:00:00',
        updated_at: '2025-01-01T00:00:00',
        summary: 'Test document summary',
        language: 'en',
        deleted: false
      },
      content: {
        summary: 'Test document summary'
      }
    },
    {
      metadata: {
        document_id: 'doc-2',
        name: 'another-file.docx',
        document_type: 'word',
        version: 1,
        size: 2048,
        created_at: '2025-01-01T00:00:00',
        updated_at: '2025-01-01T00:00:00',
        summary: 'Another document',
        language: 'es',
        deleted: false
      },
      content: {
        summary: 'Another document'
      }
    }
  ];

  const mockOnDocumentSelect = vi.fn();
  const originalConfirm = window.confirm;

  beforeEach(() => {
    vi.clearAllMocks();
    // Restore original window.confirm
    window.confirm = originalConfirm;
  });

  describe('soft delete without confirmation', () => {
    it('should delete document immediately without confirmation dialog', async () => {
      vi.mocked(documentApi.listDocuments).mockResolvedValue(mockDocuments);
      vi.mocked(documentApi.deleteDocument).mockResolvedValue({});

      // Mock window.confirm to track if it was called
      const confirmSpy = vi.fn();
      window.confirm = confirmSpy;

      render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

      await waitFor(() => {
        expect(screen.getByText('test-file.pdf')).toBeInTheDocument();
      });

      // Find and click the delete button for the first document
      const deleteButtons = screen.getAllByTitle('Delete document');
      fireEvent.click(deleteButtons[0]);

      // Should NOT show confirmation dialog
      expect(confirmSpy).not.toHaveBeenCalled();

      // Should call deleteDocument immediately
      await waitFor(() => {
        expect(documentApi.deleteDocument).toHaveBeenCalledWith('doc-1');
      });
    });

    it('should use soft delete by default (no parameters)', async () => {
      vi.mocked(documentApi.listDocuments).mockResolvedValue(mockDocuments);
      vi.mocked(documentApi.deleteDocument).mockResolvedValue({});

      render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

      await waitFor(() => {
        expect(screen.getByText('test-file.pdf')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByTitle('Delete document');
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        // Should call deleteDocument with only the document ID (no hard delete flag)
        expect(documentApi.deleteDocument).toHaveBeenCalledWith('doc-1');
        expect(documentApi.deleteDocument).toHaveBeenCalledTimes(1);
      });
    });

    it('should refresh document list after successful delete', async () => {
      vi.mocked(documentApi.listDocuments)
        .mockResolvedValueOnce(mockDocuments)
        .mockResolvedValueOnce([mockDocuments[1]]); // After delete, only second doc remains

      vi.mocked(documentApi.deleteDocument).mockResolvedValue({});

      render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

      await waitFor(() => {
        expect(screen.getByText('test-file.pdf')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByTitle('Delete document');
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        // Should call listDocuments twice (initial load + after delete)
        expect(documentApi.listDocuments).toHaveBeenCalledTimes(2);
      });
    });

    it('should handle delete errors without confirmation', async () => {
      vi.mocked(documentApi.listDocuments).mockResolvedValue(mockDocuments);
      vi.mocked(documentApi.deleteDocument).mockRejectedValue(
        new Error('Failed to delete document')
      );

      render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

      await waitFor(() => {
        expect(screen.getByText('test-file.pdf')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByTitle('Delete document');
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Failed to delete document')).toBeInTheDocument();
      });
    });

    it('should handle API error response format', async () => {
      vi.mocked(documentApi.listDocuments).mockResolvedValue(mockDocuments);

      const apiError = {
        response: {
          data: {
            detail: 'Custom delete error message'
          }
        }
      };
      vi.mocked(documentApi.deleteDocument).mockRejectedValue(apiError);

      render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

      await waitFor(() => {
        expect(screen.getByText('test-file.pdf')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByTitle('Delete document');
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Custom delete error message')).toBeInTheDocument();
      });
    });

    it('should stop event propagation when delete button is clicked', async () => {
      vi.mocked(documentApi.listDocuments).mockResolvedValue(mockDocuments);
      vi.mocked(documentApi.deleteDocument).mockResolvedValue({});

      render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

      await waitFor(() => {
        expect(screen.getByText('test-file.pdf')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByTitle('Delete document');

      // Create a mock event to track stopPropagation
      const mockEvent = new MouseEvent('click', { bubbles: true });
      const stopPropagationSpy = vi.spyOn(mockEvent, 'stopPropagation');

      // Fire the event
      fireEvent(deleteButtons[0], mockEvent);

      // The component should stop propagation to prevent document selection
      expect(stopPropagationSpy).toHaveBeenCalled();
    });

    it('should not select document when delete button is clicked', async () => {
      vi.mocked(documentApi.listDocuments).mockResolvedValue(mockDocuments);
      vi.mocked(documentApi.deleteDocument).mockResolvedValue({});

      render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

      await waitFor(() => {
        expect(screen.getByText('test-file.pdf')).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByTitle('Delete document');
      fireEvent.click(deleteButtons[0]);

      // Document select callback should NOT be called
      expect(mockOnDocumentSelect).not.toHaveBeenCalled();
    });
  });

  describe('deleted documents filtering', () => {
    it('should not display documents marked as deleted', async () => {
      const mixedDocuments = [
        ...mockDocuments,
        {
          ...mockDocuments[0],
          metadata: {
            ...mockDocuments[0].metadata,
            document_id: 'doc-3',
            name: 'deleted-file.pdf',
            deleted: true,
            deleted_at: '2025-01-02T00:00:00',
            deleted_by: 'user-123'
          }
        }
      ];

      vi.mocked(documentApi.listDocuments).mockResolvedValue(mixedDocuments);

      render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

      await waitFor(() => {
        // Should display non-deleted documents
        expect(screen.getByText('test-file.pdf')).toBeInTheDocument();
        expect(screen.getByText('another-file.docx')).toBeInTheDocument();

        // Should NOT display deleted document
        expect(screen.queryByText('deleted-file.pdf')).not.toBeInTheDocument();
      });
    });
  });

  describe('WebSocket integration', () => {
    it('should refresh documents when receiving document_updated notification', async () => {
      vi.mocked(documentApi.listDocuments).mockResolvedValue(mockDocuments);

      let notificationCallback: Function | null = null;
      vi.mocked(wsService.onSystemNotification).mockImplementation((callback) => {
        notificationCallback = callback;
        return vi.fn(); // Return unsubscribe function
      });

      render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

      await waitFor(() => {
        expect(documentApi.listDocuments).toHaveBeenCalledTimes(1);
      });

      // Simulate WebSocket notification
      if (notificationCallback) {
        notificationCallback({ type: 'document_updated' });
      }

      await waitFor(() => {
        expect(documentApi.listDocuments).toHaveBeenCalledTimes(2);
      });
    });

    it('should refresh documents when receiving document_created notification', async () => {
      vi.mocked(documentApi.listDocuments).mockResolvedValue(mockDocuments);

      let notificationCallback: Function | null = null;
      vi.mocked(wsService.onSystemNotification).mockImplementation((callback) => {
        notificationCallback = callback;
        return vi.fn(); // Return unsubscribe function
      });

      render(<DocumentList onDocumentSelect={mockOnDocumentSelect} />);

      await waitFor(() => {
        expect(documentApi.listDocuments).toHaveBeenCalledTimes(1);
      });

      // Simulate WebSocket notification
      if (notificationCallback) {
        notificationCallback({ type: 'document_created' });
      }

      await waitFor(() => {
        expect(documentApi.listDocuments).toHaveBeenCalledTimes(2);
      });
    });
  });
});