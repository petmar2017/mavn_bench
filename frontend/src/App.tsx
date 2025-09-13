import { useState, useEffect } from 'react';
import { Moon, Sun, FileText } from 'lucide-react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import classNames from 'classnames';
import styles from './App.module.css';
import { DocumentUpload } from './components/DocumentUpload';
import { DocumentList } from './components/DocumentList';
import { SearchInterface } from './components/SearchInterface';
import { wsService } from './services/websocket';
import { logger } from './services/logging';
import type { DocumentMessage } from './services/api';

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
  const [activeTab, setActiveTab] = useState('upload');
  const [toasts, setToasts] = useState<Array<{ id: string; title: string; description: string; type: string }>>([]);

  const toggleColorMode = () => {
    setColorMode(prev => prev === 'light' ? 'dark' : 'light');
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
    logger.debug('Document selected', { documentId: document.metadata.document_id, documentName: document.metadata.name });
  };

  const handleSearchResultSelect = (result: any) => {
    // Handle search result selection
    logger.debug('Search result selected', { result });
  };

  return (
    <div className={classNames(styles.app, { [styles.dark]: colorMode === 'dark' })}>
      <div className="container" style={{ paddingTop: '2rem', paddingBottom: '2rem' }}>
        <div className="flex flex-col gap-8">
          {/* Header */}
          <div className={styles.header}>
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

          <div className={styles.separator} />

          {/* Main Content */}
          <div className={styles.tabs}>
            <div className={styles.tabList}>
              <button
                className={classNames(styles.tabButton, { [styles.active]: activeTab === 'upload' })}
                onClick={() => setActiveTab('upload')}
              >
                Upload
              </button>
              <button
                className={classNames(styles.tabButton, { [styles.active]: activeTab === 'documents' })}
                onClick={() => setActiveTab('documents')}
              >
                Documents
              </button>
              <button
                className={classNames(styles.tabButton, { [styles.active]: activeTab === 'search' })}
                onClick={() => setActiveTab('search')}
              >
                Search
              </button>
            </div>

            <div className={styles.tabContent}>
              {activeTab === 'upload' && (
                <div className={styles.section}>
                  <div className={styles.sectionHeader}>
                    <h2 className={styles.sectionTitle}>Upload Document</h2>
                    <p className={styles.sectionDescription}>
                      Drag and drop or click to upload PDF, Word, Text, Markdown, CSV, or JSON files
                    </p>
                  </div>
                  <div className={styles.card}>
                    <DocumentUpload onUploadSuccess={handleUploadSuccess} />
                  </div>
                </div>
              )}

              {activeTab === 'documents' && (
                <div className={styles.section}>
                  <div className={styles.sectionHeader}>
                    <h2 className={styles.sectionTitle}>Document Library</h2>
                    <p className={styles.sectionDescription}>
                      View and manage your uploaded documents
                    </p>
                  </div>
                  <div className={styles.card}>
                    <DocumentList
                      refresh={refreshDocuments}
                      onDocumentSelect={handleDocumentSelect}
                    />
                  </div>
                </div>
              )}

              {activeTab === 'search' && (
                <div className={styles.section}>
                  <div className={styles.sectionHeader}>
                    <h2 className={styles.sectionTitle}>Search Documents</h2>
                    <p className={styles.sectionDescription}>
                      Search across your documents using vector, full-text, graph, or hybrid search
                    </p>
                  </div>
                  <div className={styles.card}>
                    <SearchInterface onResultSelect={handleSearchResultSelect} />
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Toast Notifications */}
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