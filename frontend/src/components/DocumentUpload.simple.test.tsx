import React from 'react';
import { render, screen, fireEvent, waitFor } from '../test/utils';
import { DocumentUpload } from './DocumentUpload';
import { documentApi } from '../services/api';

// Mock the API
jest.mock('../services/api', () => ({
  documentApi: {
    createDocument: jest.fn(),
  },
}));

const mockedDocumentApi = documentApi as jest.Mocked<typeof documentApi>;

describe('DocumentUpload Component', () => {
  const mockOnUploadSuccess = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render upload zone', () => {
    render(<DocumentUpload onUploadSuccess={mockOnUploadSuccess} />);

    expect(screen.getByText(/drag & drop files here/i)).toBeInTheDocument();
    expect(screen.getByText(/click to select files/i)).toBeInTheDocument();
  });

  it('should show supported file types', () => {
    render(<DocumentUpload onUploadSuccess={mockOnUploadSuccess} />);

    expect(screen.getByText(/supported formats/i)).toBeInTheDocument();
    expect(screen.getByText(/PDF/)).toBeInTheDocument();
  });

  it('should handle file upload', async () => {
    const mockDocument = { metadata: { document_id: '123', name: 'test.pdf' } };
    mockedDocumentApi.createDocument.mockResolvedValueOnce(mockDocument as any);

    render(<DocumentUpload onUploadSuccess={mockOnUploadSuccess} />);

    const dropzone = screen.getByText(/drag & drop files here/i).closest('div')!;
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });

    fireEvent.drop(dropzone, {
      dataTransfer: {
        files: [file],
        items: [{ kind: 'file', type: file.type, getAsFile: () => file }],
        types: ['Files'],
      },
    });

    await waitFor(() => {
      expect(mockedDocumentApi.createDocument).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(mockOnUploadSuccess).toHaveBeenCalledWith(mockDocument);
    });
  });
});