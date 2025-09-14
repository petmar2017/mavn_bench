import { useEffect, useState } from 'react';
import { FileText, AlertCircle, Trash2, Code, Table, FileJson } from 'lucide-react';
import classNames from 'classnames';
import { formatFileSize, formatLocalDateTime } from '../utils/format';
import { documentApi } from '../services/api';
import type { DocumentMessage } from '../services/api';
import { wsService } from '../services/websocket';
import styles from './DocumentList.module.css';

interface DocumentListProps {
  onDocumentSelect?: (document: DocumentMessage) => void;
  onDocumentDeleted?: (documentId: string) => void;
  refresh?: number;
}

export const DocumentList: React.FC<DocumentListProps> = ({ onDocumentSelect, onDocumentDeleted, refresh }) => {
  const [documents, setDocuments] = useState<DocumentMessage[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDocuments = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const docs = await documentApi.listDocuments();
      // Ensure docs is always an array
      const documentsArray = Array.isArray(docs) ? docs : [];

      // Filter out deleted documents (soft delete)
      const activeDocuments = documentsArray.filter(doc => !doc.metadata.deleted);

      // Sort documents by updated_at (or created_at if updated_at doesn't exist) in descending order
      // Latest documents first
      const sortedDocs = activeDocuments.sort((a, b) => {
        const dateA = new Date(a.metadata.updated_at || a.metadata.created_at).getTime();
        const dateB = new Date(b.metadata.updated_at || b.metadata.created_at).getTime();
        return dateB - dateA; // Descending order (latest first)
      });

      setDocuments(sortedDocs);
    } catch (err: any) {
      console.error('Failed to fetch documents:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to fetch documents');
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
    // No confirmation - just soft delete (move to trash)
    try {
      await documentApi.deleteDocument(documentId);
      fetchDocuments();
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
      <div className={styles.scrollWrapper}>
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
      </div>
    </div>
  );
};