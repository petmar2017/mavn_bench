import { useEffect, useState } from 'react';
import { FileText, AlertCircle, RotateCcw, Trash2, Code, Table, FileJson } from 'lucide-react';
import classNames from 'classnames';
import { formatFileSize, formatLocalDateTime } from '../utils/format';
import { documentApi } from '../services/api';
import type { DocumentMessage, DocumentMetadata } from '../types/document';
import styles from './DocumentList.module.css'; // Reuse same styles

interface TrashListProps {
  refresh?: number;
  onDocumentSelect?: (metadata: DocumentMetadata) => void;
}

export const TrashList: React.FC<TrashListProps> = ({ refresh, onDocumentSelect }) => {
  const [documents, setDocuments] = useState<DocumentMessage[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTrash = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const docs = await documentApi.listTrash();
      // Ensure docs is always an array
      const documentsArray = Array.isArray(docs) ? docs : [];

      // Sort documents by deleted_at in descending order (most recently deleted first)
      const sortedDocs = documentsArray.sort((a, b) => {
        const dateA = a.metadata.deleted_at ? new Date(a.metadata.deleted_at).getTime() : 0;
        const dateB = b.metadata.deleted_at ? new Date(b.metadata.deleted_at).getTime() : 0;
        return dateB - dateA; // Descending order (latest first)
      });

      setDocuments(sortedDocs);
    } catch (err: any) {
      console.error('Failed to fetch trash:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to fetch trash');
      setDocuments([]); // Set empty array on error
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTrash();
  }, [refresh]);

  const handleRestore = async (documentId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await documentApi.restoreDocument(documentId);
      fetchTrash(); // Refresh trash list
    } catch (err: any) {
      console.error('Failed to restore document:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to restore document');
    }
  };

  const handlePermanentDelete = async (documentId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to permanently delete this document? This action cannot be undone.')) {
      try {
        await documentApi.permanentlyDelete(documentId);
        fetchTrash(); // Refresh trash list
      } catch (err: any) {
        console.error('Failed to permanently delete document:', err);
        setError(err.response?.data?.detail || err.message || 'Failed to permanently delete document');
      }
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

  if (isLoading) {
    return (
      <div className={styles.loading}>
        <div className={styles.spinner} data-testid="loading-spinner" />
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
        <Trash2 size={48} className={styles.emptyIcon} />
        <div className={styles.emptyTitle}>Trash is empty</div>
        <div className={styles.emptyText}>Deleted documents will appear here</div>
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
                className={classNames(styles.tile, styles.deletedTile)}
                onClick={() => onDocumentSelect?.(doc.metadata)}
                title={doc.metadata.name || 'Untitled Document'}
              >
                <div className={styles.tileContent}>
                  <div className={styles.tileHeader}>
                    <Icon size={16} className={styles.typeIcon} />
                    <div className={styles.tileName}>
                      {doc.metadata.name || 'Untitled Document'}
                    </div>
                    <div className={styles.trashActions}>
                      <button
                        className={styles.restoreBtn}
                        onClick={(e) => handleRestore(doc.metadata.document_id, e)}
                        title="Restore document"
                      >
                        <RotateCcw size={14} />
                      </button>
                      <button
                        className={styles.deleteBtn}
                        onClick={(e) => handlePermanentDelete(doc.metadata.document_id, e)}
                        title="Permanently delete"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>

                  {doc.metadata.summary && (
                    <div className={styles.summary}>
                      {doc.metadata.summary.substring(0, 100)}
                      {doc.metadata.summary.length > 100 ? '...' : ''}
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
                      Deleted {doc.metadata.deleted_at ? new Date(doc.metadata.deleted_at).toLocaleDateString() : 'Unknown'}
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