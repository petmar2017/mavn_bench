import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '../test/utils';
import { DocumentUpload } from './DocumentUpload';
import { documentApi } from '../services/api';
import { mockDocument, createMockFile } from '../test/mocks';

// Mock the API
vi.mock('../services/api', () => ({
  documentApi: {
    createDocument: vi.fn(),
  },
}));

describe('DocumentUpload', () => {
  const mockOnUploadSuccess = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render upload zone with correct text', () => {
    render(<DocumentUpload onUploadSuccess={mockOnUploadSuccess} />);

    expect(screen.getByText(/drag & drop a file here/i)).toBeInTheDocument();
    expect(screen.getByText(/or click to select/i)).toBeInTheDocument();
  });

  it('should show supported file types', () => {
    render(<DocumentUpload onUploadSuccess={mockOnUploadSuccess} />);

    // Check for file type badges
    expect(screen.getByText('PDF')).toBeInTheDocument();
    expect(screen.getByText('Word')).toBeInTheDocument();
    expect(screen.getByText('CSV')).toBeInTheDocument();
    expect(screen.getByText('JSON')).toBeInTheDocument();
  });

  it('should handle file drop successfully', async () => {
    vi.mocked(documentApi.createDocument).mockResolvedValueOnce(mockDocument);

    render(<DocumentUpload onUploadSuccess={mockOnUploadSuccess} />);

    const dropzone = screen.getByText(/drag & drop a file here/i).closest('div')!;
    const file = createMockFile('test.pdf', 1024, 'application/pdf');

    // Simulate file drop
    fireEvent.drop(dropzone, {
      dataTransfer: {
        files: [file],
        items: [{ kind: 'file', type: file.type, getAsFile: () => file }],
        types: ['Files'],
      },
    });

    await waitFor(() => {
      expect(documentApi.createDocument).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(mockOnUploadSuccess).toHaveBeenCalledWith(mockDocument);
    });
  });

  it('should handle multiple file uploads', async () => {
    vi.mocked(documentApi.createDocument).mockResolvedValue(mockDocument);

    render(<DocumentUpload onUploadSuccess={mockOnUploadSuccess} />);

    const dropzone = screen.getByText(/drag & drop a file here/i).closest('div')!;
    const file1 = createMockFile('test1.pdf', 1024, 'application/pdf');
    const file2 = createMockFile('test2.docx', 2048, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document');

    fireEvent.drop(dropzone, {
      dataTransfer: {
        files: [file1, file2],
        items: [
          { kind: 'file', type: file1.type, getAsFile: () => file1 },
          { kind: 'file', type: file2.type, getAsFile: () => file2 },
        ],
        types: ['Files'],
      },
    });

    await waitFor(() => {
      // Component only allows single file upload (maxFiles: 1)
      expect(documentApi.createDocument).toHaveBeenCalledTimes(1);
    });
  });

  it('should show upload progress', async () => {
    // Mock a delayed upload
    vi.mocked(documentApi.createDocument).mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve(mockDocument), 100))
    );

    render(<DocumentUpload onUploadSuccess={mockOnUploadSuccess} />);

    const dropzone = screen.getByText(/drag & drop a file here/i).closest('div')!;
    const file = createMockFile('test.pdf', 1024, 'application/pdf');

    fireEvent.drop(dropzone, {
      dataTransfer: {
        files: [file],
        items: [{ kind: 'file', type: file.type, getAsFile: () => file }],
        types: ['Files'],
      },
    });

    // Wait for uploading state to appear
    await waitFor(() => {
      expect(screen.getByText(/uploading/i)).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(mockOnUploadSuccess).toHaveBeenCalled();
    });
  });

  it('should handle upload errors', async () => {
    const errorMessage = 'Upload failed';
    vi.mocked(documentApi.createDocument).mockRejectedValueOnce(
      { response: { data: { detail: errorMessage } } }
    );

    render(<DocumentUpload onUploadSuccess={mockOnUploadSuccess} />);

    const dropzone = screen.getByText(/drag & drop a file here/i).closest('div')!;
    const file = createMockFile('test.pdf', 1024, 'application/pdf');

    fireEvent.drop(dropzone, {
      dataTransfer: {
        files: [file],
        items: [{ kind: 'file', type: file.type, getAsFile: () => file }],
        types: ['Files'],
      },
    });

    await waitFor(() => {
      expect(screen.getByText(new RegExp(errorMessage, 'i'))).toBeInTheDocument();
    });

    expect(mockOnUploadSuccess).not.toHaveBeenCalled();
  });

  it('should reject unsupported file types', async () => {
    render(<DocumentUpload onUploadSuccess={mockOnUploadSuccess} />);

    const dropzone = screen.getByText(/drag & drop a file here/i).closest('div')!;
    const file = createMockFile('test.exe', 1024, 'application/x-msdownload');

    fireEvent.drop(dropzone, {
      dataTransfer: {
        files: [file],
        items: [{ kind: 'file', type: file.type, getAsFile: () => file }],
        types: ['Files'],
      },
    });

    // Should not call upload API for unsupported file type
    expect(documentApi.createDocument).not.toHaveBeenCalled();
  });

  it('should handle file size limits', async () => {
    render(<DocumentUpload onUploadSuccess={mockOnUploadSuccess} />);

    const dropzone = screen.getByText(/drag & drop a file here/i).closest('div')!;
    // Create a file larger than 10MB (assuming that's the limit)
    const largeFile = createMockFile('large.pdf', 11 * 1024 * 1024, 'application/pdf');

    fireEvent.drop(dropzone, {
      dataTransfer: {
        files: [largeFile],
        items: [{ kind: 'file', type: largeFile.type, getAsFile: () => largeFile }],
        types: ['Files'],
      },
    });

    await waitFor(() => {
      expect(screen.getByText(/file too large/i)).toBeInTheDocument();
    });

    expect(documentApi.createDocument).not.toHaveBeenCalled();
  });

  it('should clear error message after successful upload', async () => {
    // First, trigger an error
    const errorMessage = 'Upload failed';
    vi.mocked(documentApi.createDocument).mockRejectedValueOnce(new Error(errorMessage));

    render(<DocumentUpload onUploadSuccess={mockOnUploadSuccess} />);

    const dropzone = screen.getByText(/drag & drop a file here/i).closest('div')!;
    const file1 = createMockFile('test1.pdf', 1024, 'application/pdf');

    fireEvent.drop(dropzone, {
      dataTransfer: {
        files: [file1],
        items: [{ kind: 'file', type: file1.type, getAsFile: () => file1 }],
        types: ['Files'],
      },
    });

    await waitFor(() => {
      expect(screen.getByText(new RegExp(errorMessage, 'i'))).toBeInTheDocument();
    });

    // Now, upload successfully
    vi.mocked(documentApi.createDocument).mockResolvedValueOnce(mockDocument);
    const file2 = createMockFile('test2.pdf', 1024, 'application/pdf');

    fireEvent.drop(dropzone, {
      dataTransfer: {
        files: [file2],
        items: [{ kind: 'file', type: file2.type, getAsFile: () => file2 }],
        types: ['Files'],
      },
    });

    await waitFor(() => {
      expect(mockOnUploadSuccess).toHaveBeenCalled();
    });

    // Error should be cleared
    expect(screen.queryByText(new RegExp(errorMessage, 'i'))).not.toBeInTheDocument();
  });

  it('should handle drag over state', () => {
    render(<DocumentUpload onUploadSuccess={mockOnUploadSuccess} />);

    const dropzone = screen.getByText(/drag & drop a file here/i).closest('div')!;

    // Simulate drag enter
    fireEvent.dragEnter(dropzone);
    expect(dropzone).toHaveStyle({ borderColor: expect.stringContaining('blue') });

    // Simulate drag leave
    fireEvent.dragLeave(dropzone);
    expect(dropzone).not.toHaveStyle({ borderColor: expect.stringContaining('blue') });
  });

  it('should show file preview after selection', async () => {
    vi.mocked(documentApi.createDocument).mockResolvedValueOnce(mockDocument);

    render(<DocumentUpload onUploadSuccess={mockOnUploadSuccess} />);

    const dropzone = screen.getByText(/drag & drop a file here/i).closest('div')!;
    const file = createMockFile('test-document.pdf', 1024, 'application/pdf');

    fireEvent.drop(dropzone, {
      dataTransfer: {
        files: [file],
        items: [{ kind: 'file', type: file.type, getAsFile: () => file }],
        types: ['Files'],
      },
    });

    // Should show file name
    expect(screen.getByText('test-document.pdf')).toBeInTheDocument();

    await waitFor(() => {
      expect(mockOnUploadSuccess).toHaveBeenCalled();
    });
  });

  it('should be accessible with keyboard navigation', async () => {
    render(<DocumentUpload onUploadSuccess={mockOnUploadSuccess} />);

    const dropzone = screen.getByText(/drag & drop a file here/i).closest('div')!;

    // Should be focusable
    expect(dropzone).toHaveAttribute('tabIndex', '0');

    // Simulate keyboard interaction
    fireEvent.focus(dropzone);
    fireEvent.keyDown(dropzone, { key: 'Enter' });

    // This should trigger file selector, but we can't test actual file dialog
    // Just ensure it doesn't throw errors
    expect(dropzone).toBeInTheDocument();
  });
});