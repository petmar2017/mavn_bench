import { useState, useEffect } from 'react';
import { Moon, Sun, FileText, Upload, FolderOpen, Search, Trash2 } from 'lucide-react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import classNames from 'classnames';
import styles from './App.module.css';
import { DocumentUpload } from './components/DocumentUpload';
import { DocumentList } from './components/DocumentList';
import { SearchInterface } from './components/SearchInterface';
import { TrashList } from './components/TrashList';
import { Bench } from './components/Bench';
import { wsService } from './services/websocket';
import { logger } from './services/logging';
import type { DocumentMessage, SearchResult } from './services/api';
import { documentApi } from './services/api';

// Initialize logger
logger.info('Application starting', {
  environment: process.env.NODE_ENV,
  timestamp: new Date().toISOString()
});

const queryClient = new QueryClient();
logger.debug('QueryClient created');

function AppContent() {
  const [refreshDocuments, setRefreshDocuments] = useState(0);
  const [selectedDocument, setSelectedDocument] = useState<DocumentMessage | null>(null);
  const [colorMode, setColorMode] = useState<'light' | 'dark'>('light');
  const [activeTab, setActiveTab] = useState('documents');
  const [toasts, setToasts] = useState<Array<{ id: string; title: string; description: string; type: string }>>([]);

  const toggleColorMode = () => {
    setColorMode(prev => {
      const newMode = prev === 'light' ? 'dark' : 'light';
      // Apply dark class to body for global CSS variables
      if (newMode === 'dark') {
        document.body.classList.add('dark');
      } else {
        document.body.classList.remove('dark');
      }
      return newMode;
    });
  };

  const showToast = (notification: { title?: string; message: string; type?: string }) => {
    const id = Date.now().toString();
    setToasts(prev => [...prev, {
      id,
      title: notification.title || 'System Notification',
      description: notification.message,
      type: notification.type || 'info'
    }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 5000);
  };

  useEffect(() => {
    // Initialize dark mode class on body
    if (colorMode === 'dark') {
      document.body.classList.add('dark');
    } else {
      document.body.classList.remove('dark');
    }
  }, [colorMode]);

  useEffect(() => {
    // Connect to WebSocket
    wsService.connect();

    // Subscribe to system notifications
    const unsubscribe = wsService.onSystemNotification((notification) => {
      showToast(notification);
    });

    return () => {
      unsubscribe();
      wsService.disconnect();
    };
  }, []);

  const handleUploadSuccess = (document: DocumentMessage) => {
    if (document && document.metadata && document.metadata.name) {
      showToast({
        title: 'Upload successful',
        message: `${document.metadata.name} has been uploaded`,
        type: 'success'
      });
      setRefreshDocuments(prev => prev + 1);
      // Auto-switch to Documents tab after successful upload
      setActiveTab('documents');
      // Auto-select the newly uploaded document
      setSelectedDocument(document);
    } else {
      logger.error('Invalid document received on upload success', { document });
      showToast({
        title: 'Upload completed',
        message: 'Document uploaded but response was invalid',
        type: 'warning'
      });
    }
  };

  const handleDocumentSelect = (document: DocumentMessage) => {
    setSelectedDocument(document);
    logger.debug('Document selected', {
      documentId: document.metadata.document_id,
      documentName: document.metadata.name
    });
  };

  const handleSearchResultSelect = async (result: SearchResult) => {
    // Load the full document from the search result
    logger.debug('Search result selected', { result });
    try {
      const document = await documentApi.getDocument(result.document_id);
      setSelectedDocument(document);
    } catch (error) {
      logger.error('Failed to load document from search result', { error });
      showToast({
        title: 'Error',
        message: 'Failed to load document',
        type: 'error'
      });
    }
  };

  return (
    <div className={classNames(styles.app, { [styles.dark]: colorMode === 'dark' })}>
      {/* Header */}
      <div className={styles.appHeader}>
        <div className={styles.headerLeft}>
          <FileText size={32} />
          <h1>Mavn Bench</h1>
        </div>
        <div className={styles.headerRight}>
          <span className="text-sm text-gray-500">
            Document Processing Platform
          </span>
          <button
            className={styles.colorModeButton}
            aria-label="Toggle color mode"
            onClick={toggleColorMode}
          >
            {colorMode === 'light' ? <Moon size={20} /> : <Sun size={20} />}
          </button>
        </div>
      </div>

      {/* Main Layout */}
      <div className={styles.mainLayout}>
        {/* Left Sidebar */}
        <div className={styles.leftSidebar}>
          <div className={styles.sidebarTabs}>
            <button
              className={classNames(styles.sidebarTab, {
                [styles.active]: activeTab === 'upload'
              })}
              onClick={() => setActiveTab('upload')}
              title="Upload Documents"
            >
              <Upload size={20} />
              <span>Upload</span>
            </button>
            <button
              className={classNames(styles.sidebarTab, {
                [styles.active]: activeTab === 'documents'
              })}
              onClick={() => setActiveTab('documents')}
              title="Document Library"
            >
              <FolderOpen size={20} />
              <span>Documents</span>
            </button>
            <button
              className={classNames(styles.sidebarTab, {
                [styles.active]: activeTab === 'search'
              })}
              onClick={() => setActiveTab('search')}
              title="Search Documents"
            >
              <Search size={20} />
              <span>Search</span>
            </button>
            <button
              className={classNames(styles.sidebarTab, {
                [styles.active]: activeTab === 'trash'
              })}
              onClick={() => setActiveTab('trash')}
              title="Trash"
            >
              <Trash2 size={20} />
              <span>Trash</span>
            </button>
          </div>

          <div className={styles.sidebarContent}>
            {activeTab === 'upload' && (
              <div className={styles.sidebarPanel}>
                <div className={styles.panelHeader}>
                  <h2>Upload Document</h2>
                  <p>Drag and drop or click to upload files</p>
                </div>
                <DocumentUpload onUploadSuccess={handleUploadSuccess} />
              </div>
            )}

            {activeTab === 'documents' && (
              <div className={styles.sidebarPanel}>
                <div className={styles.panelHeader}>
                  <h2>Document Library</h2>
                  <p>View and manage your documents</p>
                </div>
                <DocumentList
                  refresh={refreshDocuments}
                  onDocumentSelect={handleDocumentSelect}
                />
              </div>
            )}

            {activeTab === 'search' && (
              <div className={styles.sidebarPanel}>
                <div className={styles.panelHeader}>
                  <h2>Search Documents</h2>
                  <p>Search across all your documents</p>
                </div>
                <SearchInterface onResultSelect={handleSearchResultSelect} />
              </div>
            )}
            {activeTab === 'trash' && (
              <div className={styles.sidebarPanel}>
                <div className={styles.panelHeader}>
                  <h2>Trash</h2>
                  <p>Recently deleted documents</p>
                </div>
                <TrashList refresh={refreshDocuments} />
              </div>
            )}
          </div>
        </div>

        {/* Right Bench Area */}
        <div className={styles.benchArea}>
          <Bench
            selectedDocument={selectedDocument}
            onClose={() => setSelectedDocument(null)}
          />
        </div>
      </div>

      {/* Toast Notifications */}
      <div className={styles.toastContainer}>
        {toasts.map(toast => (
          <div
            key={toast.id}
            className={classNames(styles.toast, styles[toast.type] || styles.info)}
          >
            <div className={styles.toastTitle}>{toast.title}</div>
            <div className={styles.toastDescription}>{toast.description}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function App() {
  try {
    return (
      <QueryClientProvider client={queryClient}>
        <AppContent />
      </QueryClientProvider>
    );
  } catch (error) {
    logger.error('Error rendering App', { error: String(error) });
    return <div>Error loading app: {String(error)}</div>;
  }
}

export default App;