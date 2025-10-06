import type { DocumentMessage, DocumentMetadata, DocumentContent, SearchResult } from '../services/api';

// Mock document data
export const mockDocumentMetadata: DocumentMetadata = {
  document_id: 'doc-123',
  name: 'test-document.pdf',
  document_type: 'pdf',
  version: 1,
  size: 1024000,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  processing_status: 'completed',
  tags: ['test', 'pdf'],
};

export const mockDocumentContent: DocumentContent = {
  raw_text: 'This is the raw text content of the document',
  formatted_content: '# Document Title\n\nThis is the markdown content',
  text: 'This is the raw text content of the document',
  summary: 'A brief summary of the document',
  entities: [],
  embeddings: [],
};

export const mockDocument: DocumentMessage = {
  metadata: mockDocumentMetadata,
  content: mockDocumentContent,
  tools: ['pdf-processor', 'summarizer'],
  history: [],
  audit_log: [],
};

export const mockDocuments: DocumentMessage[] = [
  mockDocument,
  {
    ...mockDocument,
    metadata: {
      ...mockDocumentMetadata,
      document_id: 'doc-456',
      name: 'another-document.docx',
      document_type: 'word',
    },
  },
  {
    ...mockDocument,
    metadata: {
      ...mockDocumentMetadata,
      document_id: 'doc-789',
      name: 'presentation.pptx',
      document_type: 'powerpoint',
      processing_status: 'processing',
    },
  },
];

export const mockSearchResult: SearchResult = {
  document_id: 'doc-123',
  score: 0.95,
  metadata: mockDocumentMetadata,
  highlights: [
    'This is a highlighted portion of the document',
    'Another relevant section',
  ],
};

export const mockSearchResults: SearchResult[] = [
  mockSearchResult,
  {
    ...mockSearchResult,
    document_id: 'doc-456',
    score: 0.85,
    metadata: {
      ...mockDocumentMetadata,
      document_id: 'doc-456',
      name: 'related-document.pdf',
    },
  },
  {
    ...mockSearchResult,
    document_id: 'doc-789',
    score: 0.72,
    metadata: {
      ...mockDocumentMetadata,
      document_id: 'doc-789',
      name: 'another-match.docx',
    },
  },
];

// Mock file for upload testing
export const createMockFile = (
  name = 'test.pdf',
  size = 1024,
  type = 'application/pdf'
): File => {
  const file = new File(['test content'], name, { type });
  Object.defineProperty(file, 'size', { value: size });
  return file;
};

// Mock API responses
export const mockApiResponses = {
  uploadSuccess: {
    status: 200,
    data: mockDocument,
  },
  uploadError: {
    status: 500,
    data: { detail: 'Upload failed' },
  },
  listDocuments: {
    status: 200,
    data: mockDocuments,
  },
  searchResults: {
    status: 200,
    data: mockSearchResults,
  },
  deleteSuccess: {
    status: 204,
    data: null,
  },
};

// Mock WebSocket events
export const mockWebSocketEvents = {
  documentCreated: {
    type: 'document_created',
    data: mockDocument,
  },
  documentUpdated: {
    type: 'document_updated',
    data: mockDocument,
  },
  documentDeleted: {
    type: 'document_deleted',
    data: { document_id: 'doc-123' },
  },
  systemNotification: {
    type: 'info',
    title: 'System Update',
    message: 'Processing complete',
  },
  errorNotification: {
    type: 'error',
    title: 'Error',
    message: 'An error occurred',
  },
};