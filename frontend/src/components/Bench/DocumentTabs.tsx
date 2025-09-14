import { X } from 'lucide-react';
import classNames from 'classnames';
import type { DocumentMessage } from '../../services/api';
import styles from './Bench.module.css';

interface DocumentTabsProps {
  documents: DocumentMessage[];
  activeDocumentId: string | null;
  unsavedChanges: Map<string, boolean>;
  onSelectDocument: (documentId: string) => void;
  onCloseDocument: (documentId: string) => void;
}

export const DocumentTabs: React.FC<DocumentTabsProps> = ({
  documents,
  activeDocumentId,
  unsavedChanges,
  onSelectDocument,
  onCloseDocument,
}) => {
  return (
    <div className={styles.tabs}>
      {documents.map((doc) => {
        const docId = doc.metadata.document_id;
        const isActive = docId === activeDocumentId;
        const hasUnsaved = unsavedChanges.get(docId) || false;

        return (
          <div
            key={docId}
            className={classNames(styles.tab, {
              [styles.activeTab]: isActive,
              [styles.unsavedTab]: hasUnsaved,
            })}
            onClick={() => onSelectDocument(docId)}
          >
            <span className={styles.tabName}>
              {hasUnsaved && <span className={styles.unsavedIndicator}>•</span>}
              {doc.metadata.name}
            </span>
            <button
              className={styles.closeTab}
              onClick={(e) => {
                e.stopPropagation();
                onCloseDocument(docId);
              }}
            >
              <X size={14} />
            </button>
          </div>
        );
      })}
    </div>
  );
};