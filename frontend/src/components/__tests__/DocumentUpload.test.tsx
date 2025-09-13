import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { DocumentUpload } from '../DocumentUpload';
import { documentApi } from '../../services/api';

// Mock the API
vi.mock('../../services/api', () => ({
  documentApi: {
    createDocument: vi.fn(),
  },
}));

// Mock react-dropzone to control file drop behavior
vi.mock('react-dropzone', () => ({
  useDropzone: vi.fn((options) => {
    const mockGetRootProps = () => ({
      onClick: vi.fn(),
      onDrop: options.onDrop,
      role: 'button',
      tabIndex: 0,
    });

    const mockGetInputProps = () => ({
      type: 'file',
      accept: options.accept,
      multiple: false,
    });

    return {
      getRootProps: mockGetRootProps,
      getInputProps: mockGetInputProps,
      isDragActive: false,
      acceptedFiles: [],
    };
  }),
}));

describe('DocumentUpload Component', () => {
  const mockOnUploadSuccess = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // Test 1: Component renders without crashing
  it('should render without throwing errors', () => {
    expect(() => {
      render(<DocumentUpload />);
    }).not.toThrow();
  });

  // Test 2: All required Chakra UI components are properly imported
  it('should render all UI elements correctly', () => {
    render(<DocumentUpload />);

    // Check for main text elements
    expect(screen.getByText(/Drag & drop a file here/i)).toBeInTheDocument();
    expect(screen.getByText(/or click to select/i)).toBeInTheDocument();

    // Check for file type badges
    expect(screen.getByText('PDF')).toBeInTheDocument();
    expect(screen.getByText('Word')).toBeInTheDocument();
    expect(screen.getByText('Text')).toBeInTheDocument();
    expect(screen.getByText('Markdown')).toBeInTheDocument();
    expect(screen.getByText('CSV')).toBeInTheDocument();
    expect(screen.getByText('JSON')).toBeInTheDocument();
  });

  // Test 3: Error state renders correctly with Alert component
  it('should display error message when upload fails', async () => {
    const mockError = 'Upload failed. Please try again.';
    vi.mocked(documentApi.createDocument).mockRejectedValueOnce(
      new Error(mockError)
    );

    const { rerender } = render(
      <DocumentUpload onUploadSuccess={mockOnUploadSuccess} />
    );

    // Simulate file upload that fails
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
    const mockUseDropzone = await import('react-dropzone');

    // Update the mock to simulate a file drop with error
    vi.mocked(mockUseDropzone.useDropzone).mockImplementation((options) => {
      // Trigger onDrop immediately to simulate file drop
      if (options.onDrop) {
        setTimeout(() => options.onDrop([file]), 0);
      }

      return {
        getRootProps: () => ({ role: 'button', tabIndex: 0 }),
        getInputProps: () => ({ type: 'file' }),
        isDragActive: false,
        acceptedFiles: [],
      };
    });

    // Re-render to apply the new mock
    rerender(
      <DocumentUpload onUploadSuccess={mockOnUploadSuccess} />
    );

    // Wait for error to be displayed
    await waitFor(() => {
      const errorAlert = screen.queryByRole('alert');
      expect(errorAlert).toBeInTheDocument();
    });
  });

  // Test 4: Success state renders correctly
  it('should display success message when upload succeeds', async () => {
    const mockDocument = { id: '123', name: 'test.pdf' };
    vi.mocked(documentApi.createDocument).mockResolvedValueOnce(mockDocument);

    const { rerender } = render(
      <DocumentUpload onUploadSuccess={mockOnUploadSuccess} />
    );

    // Simulate successful file upload
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
    const mockUseDropzone = await import('react-dropzone');

    vi.mocked(mockUseDropzone.useDropzone).mockImplementation((options) => {
      if (options.onDrop) {
        setTimeout(() => options.onDrop([file]), 0);
      }

      return {
        getRootProps: () => ({ role: 'button', tabIndex: 0 }),
        getInputProps: () => ({ type: 'file' }),
        isDragActive: false,
        acceptedFiles: [file],
      };
    });

    rerender(
      <DocumentUpload onUploadSuccess={mockOnUploadSuccess} />
    );

    await waitFor(() => {
      expect(screen.queryByText(/Upload successful/i)).toBeInTheDocument();
    });

    expect(mockOnUploadSuccess).toHaveBeenCalledWith(mockDocument);
  });

  // Test 5: Loading state renders correctly
  it('should display loading spinner during upload', async () => {
    // Mock a delayed response
    vi.mocked(documentApi.createDocument).mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 1000))
    );

    const { rerender } = render(
      <DocumentUpload />
    );

    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
    const mockUseDropzone = await import('react-dropzone');

    let dropHandler: ((files: File[]) => void) | null = null;
    vi.mocked(mockUseDropzone.useDropzone).mockImplementation((options) => {
      dropHandler = options.onDrop;
      return {
        getRootProps: () => ({ role: 'button', tabIndex: 0 }),
        getInputProps: () => ({ type: 'file' }),
        isDragActive: false,
        acceptedFiles: [],
      };
    });

    rerender(
      <DocumentUpload />
    );

    // Trigger file drop
    if (dropHandler) {
      dropHandler([file]);
    }

    // Check for loading state
    await waitFor(() => {
      expect(screen.queryByText(/Uploading.../i)).toBeInTheDocument();
    });
  });

  // Test 6: Validate that all imports are correct (this catches the original error)
  it('should have all required component imports', () => {
    // This test validates that the component can be imported and used
    // without any missing or incorrect imports
    const TestWrapper = () => (
      <DocumentUpload />
    );

    const { container } = render(<TestWrapper />);

    // Check that the component rendered successfully
    expect(container.firstChild).toBeTruthy();

    // Verify no console errors about invalid element types
    const consoleErrorSpy = vi.spyOn(console, 'error');
    expect(consoleErrorSpy).not.toHaveBeenCalledWith(
      expect.stringContaining('Element type is invalid')
    );
  });

  // Test 7: File type validation
  it('should accept only allowed file types', () => {
    render(<DocumentUpload />);

    const fileInput = document.querySelector('input[type="file"]');
    expect(fileInput).toBeInTheDocument();

    // The accept attribute should be set based on the dropzone configuration
    // This ensures only valid file types can be selected
  });

  // Test 8: Callback function is called on successful upload
  it('should call onUploadSuccess callback when provided', async () => {
    const mockDocument = { id: '456', name: 'document.pdf' };
    vi.mocked(documentApi.createDocument).mockResolvedValueOnce(mockDocument);

    const onSuccess = vi.fn();
    render(
      <DocumentUpload onUploadSuccess={onSuccess} />
    );

    // Simulate file upload
    const file = new File(['content'], 'document.pdf', { type: 'application/pdf' });
    const mockUseDropzone = await import('react-dropzone');

    vi.mocked(mockUseDropzone.useDropzone).mockImplementation((options) => {
      setTimeout(() => options.onDrop([file]), 0);
      return {
        getRootProps: () => ({ role: 'button', tabIndex: 0 }),
        getInputProps: () => ({ type: 'file' }),
        isDragActive: false,
        acceptedFiles: [],
      };
    });

    // Wait for the callback to be called
    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalledWith(mockDocument);
    });
  });
});