import { useEffect, useState, useRef, useCallback } from 'react';
import { FileText, AlertCircle, Trash2, Code, Table, FileJson } from 'lucide-react';
import classNames from 'classnames';
import { formatFileSize, formatLocalDateTime } from '../utils/format';
import { documentApi } from '../services/api';
import type { DocumentMessage } from '../services/api';
import { wsService } from '../services/websocket';
import { logger } from '../services/logging';
import styles from './DocumentList.module.css';

interface DocumentListProps {
  onDocumentSelect?: (document: DocumentMessage) => void;
  onDocumentDeleted?: (documentId: string) => void;
  refresh?: number;
}

export const DocumentList: React.FC<DocumentListProps> = ({ onDocumentSelect, onDocumentDeleted, refresh }) => {
  const [documents, setDocuments] = useState<DocumentMessage[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [currentOffset, setCurrentOffset] = useState(0);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const loadingMoreRef = useRef(false);
  const PAGINATION_LIMIT = 20; // Match backend default

  const fetchDocuments = async (append: boolean = false) => {
    console.log('[DOCLIST] fetchDocuments called!', { append, currentOffset });
    const fetchTimestamp = new Date().toISOString();
    logger.info(`[DOCLIST ${fetchTimestamp}] Starting document fetch`, {
      currentDocumentCount: documents.length,
      isCurrentlyLoading: isLoading,
      hasError: !!error,
      refreshTrigger: refresh,
      append,
      offset: append ? currentOffset : 0
    });

    if (append) {
      if (loadingMoreRef.current || !hasMore) return;
      loadingMoreRef.current = true;
      setIsLoadingMore(true);
    } else {
      setIsLoading(true);
      setError(null);
      setCurrentOffset(0);
    }

    try {
      const offset = append ? currentOffset : 0;
      logger.debug(`[DOCLIST ${fetchTimestamp}] Making API call to listDocuments with pagination`, {
        limit: PAGINATION_LIMIT,
        offset
      });
      const response = await documentApi.listDocumentsWithPagination({
        limit: PAGINATION_LIMIT,
        offset
      });
      const docs = response.documents || [];

      logger.info(`[DOCLIST ${fetchTimestamp}] API response received`, {
        rawResponse: response,
        docsCount: docs.length,
        total: response.total,
        hasMore: response.total > (offset + docs.length),
        responseType: typeof docs
      });

      // Update hasMore state
      const newHasMore = response.total > (offset + docs.length);
      setHasMore(newHasMore);

      // Ensure docs is always an array
      const documentsArray = Array.isArray(docs) ? docs : [];

      // Log the raw documents to see structure
      console.log('[DOCLIST] Raw documents from API:', documentsArray);
      if (documentsArray.length > 0) {
        console.log('[DOCLIST] First document structure:', documentsArray[0]);
        console.log('[DOCLIST] First document metadata:', documentsArray[0]?.metadata);
        console.log('[DOCLIST] First document deleted flag:', documentsArray[0]?.metadata?.deleted);
      }

      logger.debug(`[DOCLIST ${fetchTimestamp}] Processed as array`, {
        arrayLength: documentsArray.length,
        documentIds: documentsArray.map(doc => doc.metadata?.id || doc.metadata?.document_id)
      });

      // Filter out deleted documents (soft delete)
      // Only filter if the document has metadata and deleted is explicitly true
      const activeDocuments = documentsArray.filter(doc => {
        // If no metadata, include the document
        if (!doc.metadata) {
          console.warn('[DOCLIST] Document without metadata:', doc);
          return true;
        }
        // Only exclude if deleted is explicitly true
        const isDeleted = doc.metadata.deleted === true;
        if (isDeleted) {
          console.log('[DOCLIST] Filtering out deleted document:', doc.metadata.document_id);
        }
        return !isDeleted;
      });

      logger.debug(`[DOCLIST ${fetchTimestamp}] Filtered active documents`, {
        originalCount: documentsArray.length,
        activeCount: activeDocuments.length,
        deletedCount: documentsArray.length - activeDocuments.length,
        activeDocuments: activeDocuments.map(doc => ({
          id: doc.metadata?.id || doc.metadata?.document_id,
          name: doc.metadata?.name,
          type: doc.metadata?.document_type,
          deleted: doc.metadata?.deleted
        }))
      });

      // Sort documents by updated_at (or created_at if updated_at doesn't exist) in descending order
      // Latest documents first
      const sortedDocs = activeDocuments.sort((a, b) => {
        // Safely access dates with proper fallbacks
        const dateA = a.metadata?.updated_at || a.metadata?.created_at;
        const dateB = b.metadata?.updated_at || b.metadata?.created_at;

        // If either date is missing, put that document at the end
        if (!dateA && !dateB) return 0;
        if (!dateA) return 1;
        if (!dateB) return -1;

        // Convert to timestamps and sort
        const timeA = new Date(dateA).getTime();
        const timeB = new Date(dateB).getTime();
        return timeB - timeA; // Descending order (latest first)
      });

      logger.info(`[DOCLIST ${fetchTimestamp}] Documents processed and sorted`, {
        finalCount: sortedDocs.length,
        sortedDocuments: sortedDocs.map(doc => ({
          id: doc.metadata?.id,
          name: doc.metadata?.name,
          type: doc.metadata?.type,
          created_at: doc.metadata?.created_at,
          updated_at: doc.metadata?.updated_at
        }))
      });

      if (append) {
        // When appending, merge with existing documents and remove duplicates
        const existingIds = new Set(documents.map(d => d.metadata.document_id));
        const newDocs = sortedDocs.filter(d => !existingIds.has(d.metadata.document_id));
        const mergedDocs = [...documents, ...newDocs];

        // Re-sort the entire list to maintain order
        const resortedDocs = mergedDocs.sort((a, b) => {
          const dateA = a.metadata?.updated_at || a.metadata?.created_at;
          const dateB = b.metadata?.updated_at || b.metadata?.created_at;
          if (!dateA && !dateB) return 0;
          if (!dateA) return 1;
          if (!dateB) return -1;
          const timeA = new Date(dateA).getTime();
          const timeB = new Date(dateB).getTime();
          return timeB - timeA;
        });

        setDocuments(resortedDocs);
        setCurrentOffset(offset + docs.length);
        logger.debug(`[DOCLIST ${fetchTimestamp}] Appended ${newDocs.length} new documents, total: ${resortedDocs.length}`);
      } else {
        setDocuments(sortedDocs);
        setCurrentOffset(docs.length);
        logger.debug(`[DOCLIST ${fetchTimestamp}] State updated with ${sortedDocs.length} documents`);
      }

    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to fetch documents';

      logger.error(`[DOCLIST ${fetchTimestamp}] Failed to fetch documents`, {
        error: err.message,
        statusCode: err.response?.status,
        responseData: err.response?.data,
        errorStack: err.stack,
        errorType: err.name
      });

      console.error('Failed to fetch documents:', err);
      setError(errorMessage);
      setDocuments([]); // Set empty array on error

      logger.debug(`[DOCLIST ${fetchTimestamp}] Error state set`, {
        errorMessage,
        documentsCleared: true
      });
    } finally {
      if (append) {
        setIsLoadingMore(false);
        loadingMoreRef.current = false;
      } else {
        setIsLoading(false);
      }
      logger.debug(`[DOCLIST ${fetchTimestamp}] Loading state cleared`);
    }
  };

  // Handle scroll for infinite loading
  const handleScroll = useCallback(() => {
    if (!scrollContainerRef.current || isLoadingMore || !hasMore) return;

    const container = scrollContainerRef.current;
    const scrollTop = container.scrollTop;
    const scrollHeight = container.scrollHeight;
    const clientHeight = container.clientHeight;

    // Trigger when user is within 200px of bottom
    const threshold = 200;
    const distanceFromBottom = scrollHeight - (scrollTop + clientHeight);

    if (distanceFromBottom < threshold) {
      logger.debug('[DOCLIST] Scroll threshold reached, loading more documents', {
        distanceFromBottom,
        threshold,
        hasMore,
        isLoadingMore,
        currentOffset
      });
      fetchDocuments(true);
    }
  }, [hasMore, isLoadingMore, currentOffset]);

  // Fetch documents on mount and when refresh changes
  useEffect(() => {
    console.log('[DOCLIST] Component mounted or refresh changed - calling fetchDocuments, refresh:', refresh);
    fetchDocuments(false);
  }, [refresh]);

  // Fetch documents when component becomes visible (tab switched)
  useEffect(() => {
    // Always fetch when component mounts
    console.log('[DOCLIST] Component mount - fetching documents');
    fetchDocuments(false);

    // No automatic refresh - rely on WebSocket events and manual refresh
    // The refresh prop will trigger updates when needed
  }, []);

  // Add scroll listener
  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    container.addEventListener('scroll', handleScroll);
    return () => {
      container.removeEventListener('scroll', handleScroll);
    };
  }, [handleScroll]);

  useEffect(() => {
    const wsTimestamp = new Date().toISOString();
    logger.info(`[DOCLIST-WS ${wsTimestamp}] Setting up WebSocket listeners`, {
      wsConnected: wsService.isConnected(),
      wsInfo: wsService.getConnectionInfo()
    });

    // Subscribe to WebSocket events for real-time updates
    const unsubscribe = wsService.onSystemNotification((notification) => {
      const notificationTimestamp = new Date().toISOString();
      logger.info(`[DOCLIST-WS ${notificationTimestamp}] Received system notification`, {
        notification,
        notificationType: notification?.type,
        wsConnected: wsService.isConnected(),
        currentDocumentCount: documents.length
      });

      console.log('DocumentList received system notification:', notification);

      if (notification.type === 'document_created' || notification.type === 'document_updated') {
        logger.info(`[DOCLIST-WS ${notificationTimestamp}] Triggering document refresh`, {
          reason: notification.type,
          documentId: notification.document_id,
          notificationData: notification
        });

        console.log('Refreshing document list due to:', notification.type);
        fetchDocuments(false);
      } else {
        logger.debug(`[DOCLIST-WS ${notificationTimestamp}] Notification ignored - not document related`, {
          type: notification.type,
          supportedTypes: ['document_created', 'document_updated']
        });
      }
    });

    // Also listen for document-specific events
    const unsubscribeCreated = wsService.onDocumentCreated((data) => {
      const eventTimestamp = new Date().toISOString();
      logger.info(`[DOCLIST-WS ${eventTimestamp}] Document created event received`, {
        data,
        documentId: data?.id,
        wsConnected: wsService.isConnected()
      });
      fetchDocuments(false);
    });

    const unsubscribeUpdated = wsService.onDocumentUpdated((data) => {
      const eventTimestamp = new Date().toISOString();
      logger.info(`[DOCLIST-WS ${eventTimestamp}] Document updated event received`, {
        data,
        documentId: data?.id,
        wsConnected: wsService.isConnected()
      });
      fetchDocuments(false);
    });

    logger.debug(`[DOCLIST-WS ${wsTimestamp}] WebSocket event listeners registered`, {
      listenersCount: 3, // system notification, created, updated
      events: ['system:notification', 'document:created', 'document:updated']
    });

    return () => {
      logger.debug(`[DOCLIST-WS ${wsTimestamp}] Cleaning up WebSocket listeners`);
      unsubscribe();
      unsubscribeCreated();
      unsubscribeUpdated();
    };
  }, [documents.length]); // Include documents.length to get current count in logs

  const handleDelete = async (documentId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    // No confirmation - just soft delete (move to trash)
    try {
      await documentApi.deleteDocument(documentId);
      fetchDocuments(false);
      // Notify parent that document was deleted
      if (onDocumentDeleted) {
        onDocumentDeleted(documentId);
      }
    } catch (err: any) {
      console.error('Failed to delete document:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to delete document');
    }
  };

  const getDocumentIcon = (type: string) => {
    switch (type?.toLowerCase()) {
      case 'pdf': return FileText;
      case 'word': return FileText;
      case 'excel': return Table;
      case 'json': return FileJson;
      case 'markdown': return Code;
      default: return FileText;
    }
  };

  const getLanguageFlag = (lang: string) => {
    const flags: { [key: string]: string } = {
      'en': '🇬🇧',
      'es': '🇪🇸',
      'fr': '🇫🇷',
      'de': '🇩🇪',
      'it': '🇮🇹',
      'pt': '🇵🇹',
      'zh': '🇨🇳',
      'ja': '🇯🇵',
      'ko': '🇰🇷',
      'ru': '🇷🇺',
    };
    return flags[lang] || '🌐';
  };

  const getDocumentTypeBadgeClass = (type: string) => {
    const typeMap: Record<string, string> = {
      pdf: styles.pdf,
      word: styles.word,
      excel: styles.excel,
      json: styles.json,
      csv: styles.csv,
      markdown: styles.markdown,
    };
    return typeMap[type] || '';
  };

  if (isLoading) {
    return (
      <div className={styles.loading}>
        <div className={styles.spinner} />
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.error}>
        <AlertCircle size={20} className={styles.errorIcon} />
        <span>{error}</span>
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className={styles.emptyState}>
        <FileText size={48} className={styles.emptyIcon} />
        <div className={styles.emptyTitle}>No documents yet</div>
        <div className={styles.emptyText}>Upload a document to get started</div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.scrollWrapper} ref={scrollContainerRef}>
        <div className={styles.grid}>
          {documents.map((doc) => {
            const Icon = getDocumentIcon(doc.metadata.document_type);
            return (
              <div
                key={doc.metadata.document_id}
                className={styles.tile}
                onClick={() => onDocumentSelect?.(doc)}
                title={doc.metadata.name || 'Untitled Document'}
              >
                <div className={styles.tileContent}>
                  <div className={styles.tileHeader}>
                    <Icon size={16} className={styles.typeIcon} />
                    <div className={styles.tileName}>
                      {doc.metadata.name || 'Untitled Document'}
                    </div>
                    <button
                      className={styles.deleteBtn}
                      onClick={(e) => handleDelete(doc.metadata.document_id, e)}
                      title="Delete document"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>

                  {(doc.metadata.summary) && (
                    <div className={styles.summary}>
                      {(doc.metadata.summary || '').substring(0, 100)}
                      {(doc.metadata.summary || '').length > 100 ? '...' : ''}
                    </div>
                  )}

                  <div className={styles.tileFooter}>
                    <span className={classNames(
                      styles.typeBadge,
                      styles[doc.metadata.document_type?.toLowerCase() || 'default']
                    )}>
                      {(doc.metadata.document_type || 'DOC').substring(0, 3).toUpperCase()}
                    </span>
                    <span className={styles.language}>
                      {getLanguageFlag(doc.metadata.language || 'en')}
                    </span>
                    <span className={styles.size}>
                      {formatFileSize(doc.metadata.size || 0)}
                    </span>
                    <span className={styles.date}>
                      {new Date(doc.metadata.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
        {isLoadingMore && (
          <div className={styles.loadingMore}>
            <div className={styles.spinner} />
            <span>Loading more documents...</span>
          </div>
        )}
        {!hasMore && documents.length > 0 && (
          <div className={styles.endOfList}>
            <span>End of documents</span>
          </div>
        )}
      </div>
    </div>
  );
};