import { useState, useEffect } from 'react';
import { History, Clock, FileText, User, Download, RotateCcw } from 'lucide-react';
import classNames from 'classnames';
import { documentApi } from '../services/api';
import type { DocumentMessage, DocumentVersion } from '../services/api';
import { logger } from '../services/logging';
import styles from './VersionHistory.module.css';

interface VersionHistoryProps {
  documentId: string | null;
  onRestoreVersion?: (version: any) => void;
}

export const VersionHistory: React.FC<VersionHistoryProps> = ({ documentId, onRestoreVersion }) => {
  const [versions, setVersions] = useState<DocumentVersion[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedVersion, setSelectedVersion] = useState<string | null>(null);

  useEffect(() => {
    if (documentId) {
      loadVersionHistory();
    } else {
      setVersions([]);
    }
  }, [documentId]);

  const loadVersionHistory = async () => {
    if (!documentId) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await documentApi.getDocumentVersions(documentId);
      setVersions(response.data || []);
      logger.info('Loaded version history', { documentId, count: response.data?.length });
    } catch (err) {
      logger.error('Failed to load version history', { documentId, error: err });
      setError('Failed to load version history');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRestoreVersion = async (version: DocumentVersion, versionIndex: number) => {
    try {
      // For now, we'll just notify the parent since restore endpoint doesn't exist yet
      logger.info('Restore version requested', { documentId, version: version.version });

      // Notify parent component
      onRestoreVersion?.(version);

      // Show message that this feature is pending
      setError('Version restore feature is coming soon');
    } catch (err) {
      logger.error('Failed to restore version', { error: err });
      setError('Failed to restore version');
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;

    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getVersionId = (version: DocumentVersion, index: number) => {
    return `${documentId}-v${version.version}`;
  };

  if (!documentId) {
    return (
      <div className={styles.emptyState}>
        <History size={48} />
        <h3>No Document Selected</h3>
        <p>Select a document to view its version history</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className={styles.loadingState}>
        <div className={styles.spinner} />
        <p>Loading version history...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.errorState}>
        <p className={styles.errorMessage}>{error}</p>
        <button onClick={loadVersionHistory} className={styles.retryButton}>
          <RotateCcw size={16} />
          Retry
        </button>
      </div>
    );
  }

  if (versions.length === 0) {
    return (
      <div className={styles.emptyState}>
        <History size={48} />
        <h3>No Version History</h3>
        <p>This document has no previous versions</p>
      </div>
    );
  }

  return (
    <div className={styles.versionHistory}>
      <div className={styles.header}>
        <h3>
          <History size={20} />
          Version History
        </h3>
        <span className={styles.versionCount}>{versions.length} versions</span>
      </div>

      <div className={styles.versionList}>
        {versions.map((version, index) => {
          const versionId = getVersionId(version, index);
          return (
            <div
              key={versionId}
              className={classNames(styles.versionItem, {
                [styles.selected]: selectedVersion === versionId,
                [styles.current]: index === 0
              })}
              onClick={() => setSelectedVersion(versionId)}
            >
              <div className={styles.versionHeader}>
                <span className={styles.versionNumber}>
                  {index === 0 ? 'Current' : `Version ${version.version}`}
                </span>
                <span className={styles.versionDate}>
                  <Clock size={14} />
                  {formatDate(version.timestamp)}
                </span>
              </div>

              {version.commit_message && (
                <div className={styles.changeSummary}>
                  {version.commit_message}
                </div>
              )}

              <div className={styles.versionMeta}>
                {version.user && (
                  <span className={styles.author}>
                    <User size={14} />
                    {version.user}
                  </span>
                )}
                {version.changes && Object.keys(version.changes).length > 0 && (
                  <span className={styles.hash}>
                    {Object.keys(version.changes).length} changes
                  </span>
                )}
              </div>

              {selectedVersion === versionId && index !== 0 && (
                <div className={styles.versionActions}>
                  <button
                    className={styles.actionButton}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRestoreVersion(version, index);
                    }}
                    title="Restore this version"
                  >
                    <RotateCcw size={16} />
                    Restore
                  </button>
                  <button
                    className={styles.actionButton}
                    onClick={(e) => {
                      e.stopPropagation();
                      // TODO: Implement download version
                      logger.info('Download version clicked', { version: version.version });
                    }}
                    title="Download this version"
                  >
                    <Download size={16} />
                    Download
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};