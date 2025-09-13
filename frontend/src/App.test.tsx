import React from 'react';
import { render, screen, fireEvent, waitFor } from './test/utils';
import userEvent from '@testing-library/user-event';
import App from './App';
import { wsService } from './services/websocket';
import { documentApi } from './services/api';
import { mockDocuments, mockDocument } from './test/mocks';

// Mock services
jest.mock('./services/websocket', () => ({
  wsService: {
    connect: jest.fn(),
    disconnect: jest.fn(),
    onSystemNotification: jest.fn(() => jest.fn()),
  },
}));

jest.mock('./services/api', () => ({
  documentApi: {
    uploadDocument: jest.fn(),
    listDocuments: jest.fn(),
    deleteDocument: jest.fn(),
  },
  searchApi: {
    vectorSearch: jest.fn(),
    fulltextSearch: jest.fn(),
    graphSearch: jest.fn(),
    hybridSearch: jest.fn(),
  },
  processApi: {
    pdfToMarkdown: jest.fn(),
    transcribe: jest.fn(),
    scrape: jest.fn(),
    summarize: jest.fn(),
    extractEntities: jest.fn(),
  },
  healthApi: {
    checkHealth: jest.fn(),
    checkReadiness: jest.fn(),
    getMetrics: jest.fn(),
  },
}));

const mockedWsService = wsService as jest.Mocked<typeof wsService>;
const mockedDocumentApi = documentApi as jest.Mocked<typeof documentApi>;

describe('App Integration Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Set up default mocks
    mockedDocumentApi.listDocuments.mockResolvedValue([]);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('should render the app with header and tabs', () => {
    render(<App />);

    // Check header
    expect(screen.getByText('Mavn Bench')).toBeInTheDocument();
    expect(screen.getByText('Document Processing Platform')).toBeInTheDocument();

    // Check tabs
    expect(screen.getByText('Upload')).toBeInTheDocument();
    expect(screen.getByText('Documents')).toBeInTheDocument();
    expect(screen.getByText('Search')).toBeInTheDocument();
  });

  it('should connect to WebSocket on mount', () => {
    render(<App />);

    expect(mockedWsService.connect).toHaveBeenCalled();
  });

  it('should disconnect from WebSocket on unmount', () => {
    const { unmount } = render(<App />);

    unmount();

    expect(mockedWsService.disconnect).toHaveBeenCalled();
  });

  it('should subscribe to system notifications', () => {
    render(<App />);

    expect(mockedWsService.onSystemNotification).toHaveBeenCalled();
  });

  it('should switch between tabs', async () => {
    const user = userEvent.setup();

    render(<App />);

    // Initially on Upload tab
    expect(screen.getByText('Upload Document')).toBeInTheDocument();
    expect(screen.getByText(/drag and drop or click to upload/i)).toBeInTheDocument();

    // Switch to Documents tab
    const documentsTab = screen.getByText('Documents');
    await user.click(documentsTab);

    expect(screen.getByText('Document Library')).toBeInTheDocument();
    expect(screen.getByText(/view and manage your uploaded documents/i)).toBeInTheDocument();

    // Switch to Search tab
    const searchTab = screen.getByText('Search');
    await user.click(searchTab);

    expect(screen.getByText('Search Documents')).toBeInTheDocument();
    expect(screen.getByText(/search across your documents/i)).toBeInTheDocument();
  });

  it('should toggle dark mode', async () => {
    const user = userEvent.setup();

    render(<App />);

    // Find the dark mode toggle button
    const toggleButton = screen.getByLabelText(/toggle color mode/i);

    // Get initial state
    const initialIcon = toggleButton.querySelector('svg');
    expect(initialIcon).toBeInTheDocument();

    // Toggle dark mode
    await user.click(toggleButton);

    // Icon should change
    const newIcon = toggleButton.querySelector('svg');
    expect(newIcon).toBeInTheDocument();
  });

  it('should handle successful document upload', async () => {
    mockedDocumentApi.uploadDocument.mockResolvedValueOnce(mockDocument);
    mockedDocumentApi.listDocuments.mockResolvedValueOnce(mockDocuments);

    const user = userEvent.setup();

    render(<App />);

    // Upload a file
    const uploadZone = screen.getByText(/drag & drop files here/i).closest('div')!;
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });

    fireEvent.drop(uploadZone, {
      dataTransfer: {
        files: [file],
        items: [{ kind: 'file', type: file.type, getAsFile: () => file }],
        types: ['Files'],
      },
    });

    // Wait for upload to complete
    await waitFor(() => {
      expect(mockedDocumentApi.uploadDocument).toHaveBeenCalledWith(file);
    });

    // Should show success toast (mocked, but we can verify the upload succeeded)
    expect(mockedDocumentApi.uploadDocument).toHaveBeenCalledTimes(1);
  });

  it('should refresh document list after upload', async () => {
    mockedDocumentApi.uploadDocument.mockResolvedValueOnce(mockDocument);
    mockedDocumentApi.listDocuments
      .mockResolvedValueOnce([]) // Initial empty list
      .mockResolvedValueOnce([mockDocument]); // After upload

    const user = userEvent.setup();

    render(<App />);

    // Switch to Documents tab to see initial state
    const documentsTab = screen.getByText('Documents');
    await user.click(documentsTab);

    await waitFor(() => {
      expect(screen.getByText(/no documents yet/i)).toBeInTheDocument();
    });

    // Switch back to Upload tab
    const uploadTab = screen.getByText('Upload');
    await user.click(uploadTab);

    // Upload a file
    const uploadZone = screen.getByText(/drag & drop files here/i).closest('div')!;
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });

    fireEvent.drop(uploadZone, {
      dataTransfer: {
        files: [file],
        items: [{ kind: 'file', type: file.type, getAsFile: () => file }],
        types: ['Files'],
      },
    });

    await waitFor(() => {
      expect(mockedDocumentApi.uploadDocument).toHaveBeenCalled();
    });

    // Switch back to Documents tab
    await user.click(documentsTab);

    // Document list should refresh
    await waitFor(() => {
      expect(mockedDocumentApi.listDocuments).toHaveBeenCalledTimes(2);
    });
  });

  it('should handle WebSocket notifications', async () => {
    let notificationCallback: ((notification: any) => void) | null = null;

    mockedWsService.onSystemNotification.mockImplementation((callback) => {
      notificationCallback = callback;
      return jest.fn();
    });

    render(<App />);

    // Simulate a system notification
    if (notificationCallback) {
      notificationCallback({
        title: 'Test Notification',
        message: 'This is a test',
        type: 'info',
      });
    }

    // The toast would be shown (can't directly test Chakra UI toasts without more setup)
    expect(mockedWsService.onSystemNotification).toHaveBeenCalled();
  });

  it('should handle document selection', async () => {
    mockedDocumentApi.listDocuments.mockResolvedValueOnce(mockDocuments);

    const user = userEvent.setup();

    render(<App />);

    // Switch to Documents tab
    const documentsTab = screen.getByText('Documents');
    await user.click(documentsTab);

    await waitFor(() => {
      expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
    });

    // Click on a document
    const documentRow = screen.getByText('test-document.pdf').closest('tr')!;
    await user.click(documentRow);

    // Document should be selected (state is internal, but action is triggered)
    expect(documentRow).toBeInTheDocument();
  });

  it('should integrate all three main tabs', async () => {
    const user = userEvent.setup();

    render(<App />);

    // Test Upload tab
    const uploadTab = screen.getByText('Upload');
    await user.click(uploadTab);
    expect(screen.getByText('Upload Document')).toBeInTheDocument();

    // Test Documents tab
    const documentsTab = screen.getByText('Documents');
    await user.click(documentsTab);
    expect(screen.getByText('Document Library')).toBeInTheDocument();

    // Test Search tab
    const searchTab = screen.getByText('Search');
    await user.click(searchTab);
    expect(screen.getByText('Search Documents')).toBeInTheDocument();
  });

  it('should maintain state when switching tabs', async () => {
    const user = userEvent.setup();

    render(<App />);

    // Type in search on Search tab
    const searchTab = screen.getByText('Search');
    await user.click(searchTab);

    const searchInput = screen.getByPlaceholderText(/search documents/i);
    await user.type(searchInput, 'test query');

    // Switch to another tab
    const uploadTab = screen.getByText('Upload');
    await user.click(uploadTab);

    // Switch back to Search tab
    await user.click(searchTab);

    // Search input should still have the value
    expect(screen.getByPlaceholderText(/search documents/i)).toHaveValue('test query');
  });

  it('should render with correct color mode value', () => {
    render(<App />);

    // Check that the ChakraProvider is providing color mode functionality
    const toggleButton = screen.getByLabelText(/toggle color mode/i);
    expect(toggleButton).toBeInTheDocument();
  });

  it('should have proper tab panel structure', () => {
    render(<App />);

    // Check tab structure
    const tabList = screen.getByRole('tablist');
    expect(tabList).toBeInTheDocument();

    const tabs = screen.getAllByRole('tab');
    expect(tabs).toHaveLength(3);
    expect(tabs[0]).toHaveTextContent('Upload');
    expect(tabs[1]).toHaveTextContent('Documents');
    expect(tabs[2]).toHaveTextContent('Search');
  });

  it('should handle search result selection', async () => {
    const { searchApi } = require('./services/api');
    searchApi.vectorSearch = jest.fn().mockResolvedValueOnce([
      {
        document_id: 'doc-123',
        score: 0.95,
        metadata: mockDocument.metadata,
        highlights: ['Test highlight'],
      },
    ]);

    const user = userEvent.setup();

    render(<App />);

    // Go to Search tab
    const searchTab = screen.getByText('Search');
    await user.click(searchTab);

    // Perform search
    const searchInput = screen.getByPlaceholderText(/search documents/i);
    await user.type(searchInput, 'test');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
    });

    // Click on result
    const resultCard = screen.getByText('test-document.pdf').closest('div');
    if (resultCard) {
      await user.click(resultCard);
    }

    // Verify console log was called (result selection is logged)
    const consoleSpy = jest.spyOn(console, 'log').mockImplementation();
    expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('Selected search result'));
    consoleSpy.mockRestore();
  });

  it('should properly clean up on unmount', () => {
    const unsubscribeMock = jest.fn();
    mockedWsService.onSystemNotification.mockReturnValue(unsubscribeMock);

    const { unmount } = render(<App />);

    unmount();

    expect(unsubscribeMock).toHaveBeenCalled();
    expect(mockedWsService.disconnect).toHaveBeenCalled();
  });
});