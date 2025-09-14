import React from 'react';
import { Trash2, Download, History } from 'lucide-react';
import styles from './ViewerToolbar.module.css';

interface ViewerToolbarProps {
  documentId: string;
  isDeleted?: boolean;
  onDelete?: () => void;
  onDownload?: () => void;
  onHistory?: () => void;
  children?: React.ReactNode;
}

export const ViewerToolbar: React.FC<ViewerToolbarProps> = ({
  documentId,
  isDeleted = false,
  onDelete,
  onDownload,
  onHistory,
  children
}) => {
  return (
    <div className={styles.toolbar}>
      <div className={styles.leftActions}>
        {children}
      </div>

      <div className={styles.rightActions}>
        {onDelete && (
          <button
            className={styles.actionButton}
            onClick={onDelete}
            title={isDeleted ? "Permanently delete document" : "Delete document"}
          >
            <Trash2 size={18} />
          </button>
        )}

        {onDownload && (
          <button
            className={styles.actionButton}
            onClick={onDownload}
            title="Download document"
          >
            <Download size={18} />
          </button>
        )}

        {onHistory && (
          <button
            className={styles.actionButton}
            onClick={onHistory}
            title="Version history"
          >
            <History size={18} />
          </button>
        )}
      </div>
    </div>
  );
};