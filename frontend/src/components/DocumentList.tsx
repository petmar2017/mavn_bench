import { useEffect, useState } from 'react';
import { FileText, Calendar, HardDrive, AlertCircle, Eye, Download, Trash2 } from 'lucide-react';
import classNames from 'classnames';
import { documentApi } from '../services/api';
import type { DocumentMessage } from '../services/api';
import { wsService } from '../services/websocket';
import styles from './DocumentList.module.css';

interface DocumentListProps {
  onDocumentSelect?: (document: DocumentMessage) => void;
  refresh?: number;
}

export const DocumentList: React.FC<DocumentListProps> = ({ onDocumentSelect, refresh }) => {
  const [documents, setDocuments] = useState<DocumentMessage[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDocuments = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const docs = await documentApi.listDocuments();
      // Ensure docs is always an array
      setDocuments(Array.isArray(docs) ? docs : []);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch documents');
      setDocuments([]); // Set empty array on error
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [refresh]);

  useEffect(() => {
    // Subscribe to WebSocket events for real-time updates
    const unsubscribe = wsService.onSystemNotification((notification) => {
      if (notification.type === 'document_created' || notification.type === 'document_updated') {
        fetchDocuments();
      }
    });

    return () => {
      unsubscribe();
    };
  }, []);

  const handleDelete = async (documentId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to delete this document?')) {
      try {
        await documentApi.deleteDocument(documentId);
        fetchDocuments();
      } catch (err: any) {
        console.error('Failed to delete document:', err);
      }
    }
  };

  const handleView = (doc: DocumentMessage, e: React.MouseEvent) => {
    e.stopPropagation();
    onDocumentSelect?.(doc);
  };

  const handleDownload = async (doc: DocumentMessage, e: React.MouseEvent) => {
    e.stopPropagation();
    // TODO: Implement download functionality
    console.log('Download document:', doc.metadata.document_id);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDate = (dateString: string) => {
    // Parse the UTC date from server and convert to local timezone
    const date = new Date(dateString);

    // Use toLocaleString to properly display date and time in user's timezone
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,  // Use 12-hour format with AM/PM
      timeZoneName: 'short'  // Optionally show timezone abbreviation
    });
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
      <div className={styles.grid}>
        {documents.map((doc) => (
          <div
            key={doc.metadata.document_id}
            className={styles.card}
            onClick={() => onDocumentSelect?.(doc)}
          >
            <div className={styles.cardHeader}>
              <FileText size={20} className={styles.fileIcon} />
              <div className={styles.cardTitle}>
                {doc.metadata.name}
                <div style={{ fontSize: '10px', color: '#666' }}>
                  ID: {doc.metadata.document_id || 'undefined'}
                </div>
              </div>
            </div>

            <div className={styles.cardBody}>
              <div className={styles.metadata}>
                <span className={classNames(styles.badge, getDocumentTypeBadgeClass(doc.metadata.document_type))}>
                  {doc.metadata.document_type.toUpperCase()}
                </span>

                <div className={styles.metadataItem}>
                  <HardDrive size={12} className={styles.metadataIcon} />
                  <span>{formatFileSize(doc.metadata.size || 0)}</span>
                </div>

                <div className={styles.metadataItem}>
                  <Calendar size={12} className={styles.metadataIcon} />
                  <span>{formatDate(doc.metadata.created_at)}</span>
                </div>
              </div>

              {doc.content?.text && (
                <div className={styles.contentPreview}>
                  {doc.content.text.substring(0, 150)}...
                </div>
              )}

              <div className={styles.actions}>
                <button
                  className={styles.actionButton}
                  onClick={(e) => handleView(doc, e)}
                  title="View document"
                >
                  <Eye size={16} /> View
                </button>
                <button
                  className={styles.actionButton}
                  onClick={(e) => handleDownload(doc, e)}
                  title="Download document"
                >
                  <Download size={16} /> Download
                </button>
                <button
                  className={classNames(styles.actionButton, styles.danger)}
                  onClick={(e) => handleDelete(doc.metadata.document_id, e)}
                  title="Delete document"
                >
                  <Trash2 size={16} /> Delete
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};