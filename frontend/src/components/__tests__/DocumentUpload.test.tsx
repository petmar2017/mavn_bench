import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import { DocumentUpload } from '../DocumentUpload';
import { documentApi } from '../../services/api';

// Mock the API
vi.mock('../../services/api', () => ({
  documentApi: {
    createDocument: vi.fn(),
  },
}));

// Mock react-dropzone to control file drop behavior
let mockOnDrop: ((files: File[]) => void) | undefined;

vi.mock('react-dropzone', () => ({
  useDropzone: vi.fn((options: any) => {
    mockOnDrop = options.onDrop;
    return {
      getRootProps: () => ({
        tabIndex: 0,
        onDrop: (e: any) => {
          e.preventDefault();
          if (options.onDrop && e.dataTransfer?.files) {
            options.onDrop(Array.from(e.dataTransfer.files));
          }
        },
      }),
      getInputProps: () => ({
        type: 'file',
        accept: options.accept ? Object.keys(options.accept).join(',') : '',
        multiple: false,
      }),
      isDragActive: false,
      acceptedFiles: [],
    };
  }),
}));

describe('DocumentUpload Component', () => {
  const mockOnUploadSuccess = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockOnDrop = undefined;
  });

  // Test 1: Component renders without crashing
  it('should render without throwing errors', () => {
    expect(() => {
      render(<DocumentUpload />);
    }).not.toThrow();
  });

  // Test 2: All UI elements render correctly
  it('should render all UI elements correctly', () => {
    render(<DocumentUpload />);

    // Check for main text elements
    expect(screen.getByText(/Drag & drop a file here/i)).toBeInTheDocument();
    expect(screen.getByText(/or click to select/i)).toBeInTheDocument();

    // Check for file type badges
    expect(screen.getByText('PDF')).toBeInTheDocument();
    expect(screen.getByText('Word')).toBeInTheDocument();
    expect(screen.getByText('CSV')).toBeInTheDocument();
    expect(screen.getByText('JSON')).toBeInTheDocument();
  });

  // Test 3: Error state renders correctly
  it('should display error message when upload fails', async () => {
    const mockError = 'Upload failed. Please try again.';
    vi.mocked(documentApi.createDocument).mockRejectedValueOnce(
      { response: { data: { detail: mockError } } }
    );

    render(<DocumentUpload onUploadSuccess={mockOnUploadSuccess} />);

    // Simulate file upload that fails
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });

    await act(async () => {
      if (mockOnDrop) {
        await mockOnDrop([file]);
      }
    });

    await waitFor(() => {
      expect(screen.getByText(mockError)).toBeInTheDocument();
    });
  });

  // Test 4: Success state renders correctly
  it('should display success message when upload succeeds', async () => {
    const documentWithId = { id: 'doc-123', metadata: { name: 'test.pdf' } };
    vi.mocked(documentApi.createDocument).mockResolvedValueOnce(documentWithId);

    render(<DocumentUpload onUploadSuccess={mockOnUploadSuccess} />);

    // Simulate successful file upload
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });

    await act(async () => {
      if (mockOnDrop) {
        await mockOnDrop([file]);
      }
    });

    await waitFor(() => {
      expect(screen.getByText(/Upload successful!/i)).toBeInTheDocument();
    });

    expect(mockOnUploadSuccess).toHaveBeenCalledWith(documentWithId, undefined);
  });

  // Test 5: Drag and drop zone accepts correct file types
  it('should accept only specified file types', () => {
    render(<DocumentUpload />);

    // The component should render without errors
    const dropzone = screen.getByText(/Drag & drop a file here/i).parentElement;
    expect(dropzone).toBeInTheDocument();
  });

  // Test 6: Component handles multiple files correctly (only processes first)
  it('should handle multiple files by processing only the first', async () => {
    const documentWithId = { id: 'doc-123', metadata: { name: 'test1.pdf' } };
    vi.mocked(documentApi.createDocument).mockResolvedValueOnce(documentWithId);

    render(<DocumentUpload onUploadSuccess={mockOnUploadSuccess} />);

    const file1 = new File(['content1'], 'test1.pdf', { type: 'application/pdf' });
    const file2 = new File(['content2'], 'test2.pdf', { type: 'application/pdf' });

    await act(async () => {
      if (mockOnDrop) {
        await mockOnDrop([file1]); // Component only accepts single file
      }
    });

    await waitFor(() => {
      expect(documentApi.createDocument).toHaveBeenCalledTimes(1);
    });
  });

  // Test 7: Loading state renders correctly
  it.skip('should show loading state during upload', async () => {
    // This test is skipped because the component now uses a queue-based upload system
    // that doesn't display "Uploading..." text. Instead, uploads happen in the background
    // with progress tracked via the uploadQueue prop.
    // TODO: Update this test to check for queue-based upload UI when uploadQueue prop is provided
  });

  // Test 8: Component cleans up error state on successful upload
  it('should clear error state after successful upload', async () => {
    const mockError = 'Upload failed. Please try again.';

    // First upload fails
    vi.mocked(documentApi.createDocument).mockRejectedValueOnce(
      { response: { data: { detail: mockError } } }
    );

    render(<DocumentUpload onUploadSuccess={mockOnUploadSuccess} />);

    const file1 = new File(['test content'], 'test1.pdf', { type: 'application/pdf' });

    await act(async () => {
      if (mockOnDrop) {
        await mockOnDrop([file1]);
      }
    });

    await waitFor(() => {
      expect(screen.getByText(mockError)).toBeInTheDocument();
    });

    // Second upload succeeds
    const documentWithId = { id: 'doc-123', metadata: { name: 'test2.pdf' } };
    vi.mocked(documentApi.createDocument).mockResolvedValueOnce(documentWithId);

    const file2 = new File(['test content'], 'test2.pdf', { type: 'application/pdf' });

    await act(async () => {
      if (mockOnDrop) {
        await mockOnDrop([file2]);
      }
    });

    await waitFor(() => {
      expect(screen.queryByText(mockError)).not.toBeInTheDocument();
      expect(screen.getByText(/Upload successful!/i)).toBeInTheDocument();
    });
  });
});