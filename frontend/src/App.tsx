import { useState, useEffect, useRef } from 'react';
import { Moon, Sun, FileText, Upload, FolderOpen, Search, Trash2, History } from 'lucide-react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import classNames from 'classnames';
import styles from './App.module.css';
import { DocumentUpload } from './components/DocumentUpload';
import { DocumentList } from './components/DocumentList';
import { SearchInterface } from './components/SearchInterface';
import { TrashList } from './components/TrashList';
import { VersionHistory } from './components/VersionHistory';
import { UploadQueue, type UploadItem } from './components/UploadQueue';
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
  const [colorMode, setColorMode] = useState<'light' | 'dark'>('dark');
  const [activeTab, setActiveTab] = useState('documents');
  const [toasts, setToasts] = useState<Array<{ id: string; title: string; description: string; type: string }>>([]);
  const [versionHistoryDocumentId, setVersionHistoryDocumentId] = useState<string | null>(null);
  const [uploadQueue, setUploadQueue] = useState<UploadItem[]>([]);
  const uploadQueueRef = useRef<UploadItem[]>([]);
  const benchRef = useRef<any>(null);

  // Search state - persists across tab switches
  const [searchState, setSearchState] = useState({
    query: '',
    searchType: 'vector' as any,
    results: [] as any[],
    hasSearched: false,
    error: null as string | null
  });

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

    // Subscribe to queue events
    const unsubQueue = wsService.on('queue:job_progress', (data: any) => {
      // Update upload item progress
      if (data.job_id) {
        const uploadItem = uploadQueueRef.current.find(item => item.jobId === data.job_id);
        if (uploadItem) {
          updateUploadItem(uploadItem.id, {
            progress: data.progress,
            status: 'processing'
          });
        }
      }
    });

    const unsubComplete = wsService.on('queue:job_completed', (data: any) => {
      // Mark upload as completed
      if (data.job_id) {
        const uploadItem = uploadQueueRef.current.find(item => item.jobId === data.job_id);
        if (uploadItem) {
          updateUploadItem(uploadItem.id, {
            status: 'completed',
            progress: 100
          });
          // Refresh documents list
          setRefreshDocuments(prev => prev + 1);
        }
      }
    });

    const unsubFailed = wsService.on('queue:job_failed', (data: any) => {
      // Mark upload as failed
      if (data.job_id) {
        const uploadItem = uploadQueueRef.current.find(item => item.jobId === data.job_id);
        if (uploadItem) {
          updateUploadItem(uploadItem.id, {
            status: 'error',
            error: data.error_message || 'Processing failed'
          });
        }
      }
    });

    return () => {
      unsubscribe();
      unsubQueue();
      unsubComplete();
      unsubFailed();
      wsService.disconnect();
    };
  }, []); // Empty dependency array - only connect once on mount

  // Upload queue management functions
  const addToUploadQueue = (file: File): string => {
    const itemId = `upload-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const uploadItem: UploadItem = {
      id: itemId,
      fileName: file.name,
      fileSize: file.size,
      fileType: file.type || 'unknown',
      status: 'pending',
      progress: 0,
      startTime: Date.now()
    };

    setUploadQueue(prev => [...prev, uploadItem]);
    logger.info('Added file to upload queue', { fileName: file.name, itemId });
    return itemId;
  };

  // Keep ref in sync with state
  useEffect(() => {
    uploadQueueRef.current = uploadQueue;
  }, [uploadQueue]);

  const updateUploadItem = (id: string, updates: Partial<UploadItem>) => {
    setUploadQueue(prev => prev.map(item =>
      item.id === id ? { ...item, ...updates } : item
    ));
  };

  const removeFromQueue = (id: string) => {
    setUploadQueue(prev => prev.filter(item => item.id !== id));
    logger.info('Removed item from upload queue', { itemId: id });
  };

  const clearCompletedUploads = () => {
    setUploadQueue(prev => prev.filter(item => item.status !== 'completed'));
    logger.info('Cleared completed uploads from queue');
  };

  const handleUploadSuccess = (document: DocumentMessage, uploadId?: string) => {
    if (uploadId) {
      updateUploadItem(uploadId, {
        status: 'completed',
        progress: 100,
        documentId: document.metadata.document_id
      });
    }

    if (document && document.metadata && document.metadata.name) {
      showToast({
        title: 'Upload successful',
        message: `${document.metadata.name} has been uploaded`,
        type: 'success'
      });
      // Auto-switch to Documents tab FIRST
      setActiveTab('documents');
      // Then trigger refresh after a small delay to ensure component mounts
      setTimeout(() => {
        setRefreshDocuments(prev => prev + 1);
      }, 100);
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

  const handleDocumentDeleted = (documentId: string) => {
    // Close the tab in the Bench if it's open
    if (benchRef.current) {
      benchRef.current.closeDocument(documentId);
    }
    logger.info('Document deleted and tab closed', { documentId });
  };

  const handleSearchResultSelect = async (result: SearchResult) => {
    // Load the full document from the search result
    logger.debug('Search result selected', { result });
    try {
      const document = await documentApi.getDocument(result.document_id);
      logger.debug('Document fetched', { document });

      // Check if document has the expected structure
      if (!document || !document.metadata) {
        logger.error('Invalid document structure', { document });
        showToast({
          title: 'Error',
          message: 'Invalid document format received',
          type: 'error'
        });
        return;
      }

      setSelectedDocument(document);
      logger.debug('Document set as selected', { documentId: document.metadata.document_id });
    } catch (error) {
      logger.error('Failed to load document from search result', { error });
      showToast({
        title: 'Error',
        message: 'Failed to load document',
        type: 'error'
      });
    }
  };

  const handleSearchResultDelete = (documentId: string) => {
    // If the deleted document is currently selected in Bench, close it
    if (selectedDocument?.metadata?.document_id === documentId) {
      setSelectedDocument(null);
    }
    // Also close the tab in Bench if it's open
    if (benchRef.current) {
      benchRef.current.closeDocument(documentId);
    }
    // Refresh the document list
    setRefreshDocuments(prev => prev + 1);
    showToast({
      title: 'Document deleted',
      message: 'Document moved to trash',
      type: 'success'
    });
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
            <button
              className={classNames(styles.sidebarTab, {
                [styles.active]: activeTab === 'history'
              })}
              onClick={() => setActiveTab('history')}
              title="Version History"
            >
              <History size={20} />
              <span>History</span>
            </button>
          </div>

          <div className={styles.sidebarContent}>
            {activeTab === 'upload' && (
              <div className={styles.sidebarPanel}>
                <div className={styles.uploadPanel}>
                  <DocumentUpload
                    onUploadSuccess={handleUploadSuccess}
                    onFileSelect={addToUploadQueue}
                    updateUploadItem={updateUploadItem}
                    uploadQueue={uploadQueue}
                  />
                  <div className={styles.uploadQueueContainer}>
                    <UploadQueue
                      queue={uploadQueue}
                      onRemoveItem={removeFromQueue}
                      onClearCompleted={clearCompletedUploads}
                    />
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'documents' && (
              <div className={styles.sidebarPanel}>
                <DocumentList
                  refresh={refreshDocuments}
                  onDocumentSelect={handleDocumentSelect}
                  onDocumentDeleted={handleDocumentDeleted}
                />
              </div>
            )}

            {activeTab === 'search' && (
              <div className={styles.sidebarPanel}>
                <SearchInterface
                  onResultSelect={handleSearchResultSelect}
                  onResultDelete={handleSearchResultDelete}
                  searchState={searchState}
                  onSearchStateChange={setSearchState}
                />
              </div>
            )}
            {activeTab === 'trash' && (
              <div className={styles.sidebarPanel}>
                <TrashList
                  refresh={refreshDocuments}
                  onDocumentSelect={handleDocumentSelect}
                />
              </div>
            )}
            {activeTab === 'history' && (
              <div className={styles.sidebarPanel}>
                <VersionHistory
                  documentId={versionHistoryDocumentId}
                  onRestoreVersion={(version) => {
                    // Refresh documents list after restore
                    setRefreshDocuments(prev => prev + 1);
                    showToast({
                      title: 'Version restored',
                      message: 'Document has been restored to selected version',
                      type: 'success'
                    });
                  }}
                />
              </div>
            )}
          </div>
        </div>

        {/* Right Bench Area */}
        <div className={styles.benchArea}>
          <Bench
            ref={benchRef}
            selectedDocument={selectedDocument}
            onClose={() => setSelectedDocument(null)}
            onHistoryClick={(documentId) => {
              setVersionHistoryDocumentId(documentId);
              setActiveTab('history');
            }}
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