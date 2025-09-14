import { useState, useEffect } from 'react';
import { Upload, CheckCircle, XCircle, Loader, X, FileText, AlertCircle } from 'lucide-react';
import classNames from 'classnames';
import styles from './UploadQueue.module.css';

export interface UploadItem {
  id: string;
  fileName: string;
  fileSize: number;
  fileType: string;
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'error';
  progress: number;
  error?: string;
  documentId?: string;
  startTime: number;
}

interface UploadQueueProps {
  queue: UploadItem[];
  onRemoveItem?: (id: string) => void;
  onRetryItem?: (id: string) => void;
  onClearCompleted?: () => void;
}

export const UploadQueue: React.FC<UploadQueueProps> = ({
  queue,
  onRemoveItem,
  onRetryItem,
  onClearCompleted
}) => {
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getElapsedTime = (startTime: number): string => {
    const elapsed = Date.now() - startTime;
    const seconds = Math.floor(elapsed / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    return `${minutes}m ${seconds % 60}s`;
  };

  const getStatusIcon = (status: UploadItem['status']) => {
    switch (status) {
      case 'pending':
        return <AlertCircle size={16} className={styles.pendingIcon} />;
      case 'uploading':
      case 'processing':
        return <Loader size={16} className={styles.spinner} />;
      case 'completed':
        return <CheckCircle size={16} className={styles.successIcon} />;
      case 'error':
        return <XCircle size={16} className={styles.errorIcon} />;
    }
  };

  const getStatusText = (item: UploadItem): string => {
    switch (item.status) {
      case 'pending':
        return 'Waiting...';
      case 'uploading':
        return `Uploading... ${item.progress}%`;
      case 'processing':
        return 'Processing document...';
      case 'completed':
        return 'Completed';
      case 'error':
        return 'Failed';
    }
  };

  const completedCount = queue.filter(item => item.status === 'completed').length;
  const activeCount = queue.filter(item => 
    item.status === 'uploading' || item.status === 'processing' || item.status === 'pending'
  ).length;
  const errorCount = queue.filter(item => item.status === 'error').length;

  if (queue.length === 0) {
    return (
      <div className={styles.emptyQueue}>
        <Upload size={32} />
        <p>No uploads in progress</p>
        <span className={styles.hint}>Selected files will appear here</span>
      </div>
    );
  }

  return (
    <div className={styles.uploadQueue}>
      <div className={styles.queueHeader}>
        <h3>
          <Upload size={18} />
          Upload Queue
        </h3>
        <div className={styles.queueStats}>
          {activeCount > 0 && (
            <span className={styles.activeCount}>{activeCount} active</span>
          )}
          {completedCount > 0 && (
            <span className={styles.completedCount}>{completedCount} completed</span>
          )}
          {errorCount > 0 && (
            <span className={styles.errorCount}>{errorCount} failed</span>
          )}
        </div>
      </div>

      {completedCount > 0 && (
        <div className={styles.queueActions}>
          <button
            className={styles.clearButton}
            onClick={onClearCompleted}
            title="Clear completed uploads"
          >
            Clear Completed
          </button>
        </div>
      )}

      <div className={styles.queueItems}>
        {queue.map((item) => (
          <div
            key={item.id}
            className={classNames(styles.queueItem, {
              [styles.pending]: item.status === 'pending',
              [styles.uploading]: item.status === 'uploading',
              [styles.processing]: item.status === 'processing',
              [styles.completed]: item.status === 'completed',
              [styles.error]: item.status === 'error',
            })}
          >
            <div className={styles.itemHeader}>
              <div className={styles.itemInfo}>
                <FileText size={16} />
                <div className={styles.itemDetails}>
                  <span className={styles.fileName}>{item.fileName}</span>
                  <div className={styles.itemMeta}>
                    <span className={styles.fileSize}>{formatFileSize(item.fileSize)}</span>
                    <span className={styles.separator}>•</span>
                    <span className={styles.fileType}>{item.fileType}</span>
                    {(item.status === 'uploading' || item.status === 'processing') && (
                      <>
                        <span className={styles.separator}>•</span>
                        <span className={styles.elapsed}>{getElapsedTime(item.startTime)}</span>
                      </>
                    )}
                  </div>
                </div>
              </div>
              <div className={styles.itemActions}>
                {getStatusIcon(item.status)}
                <span className={styles.statusText}>{getStatusText(item)}</span>
                {item.status === 'error' && onRetryItem && (
                  <button
                    className={styles.retryButton}
                    onClick={() => onRetryItem(item.id)}
                    title="Retry upload"
                  >
                    Retry
                  </button>
                )}
                {(item.status === 'completed' || item.status === 'error') && onRemoveItem && (
                  <button
                    className={styles.removeButton}
                    onClick={() => onRemoveItem(item.id)}
                    title="Remove from queue"
                  >
                    <X size={14} />
                  </button>
                )}
              </div>
            </div>

            {item.status === 'uploading' && (
              <div className={styles.progressBar}>
                <div
                  className={styles.progressFill}
                  style={{ width: `${item.progress}%` }}
                />
              </div>
            )}

            {item.status === 'error' && item.error && (
              <div className={styles.errorMessage}>
                {item.error}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};