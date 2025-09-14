import { useRef, useEffect } from 'react';
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
  onDeleteDocument?: (documentId: string, isHardDelete: boolean) => void;
}

export const DocumentTabs: React.FC<DocumentTabsProps> = ({
  documents,
  activeDocumentId,
  unsavedChanges,
  onSelectDocument,
  onCloseDocument,
  onDeleteDocument,
}) => {
  const tabsContainerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to the active tab when it changes
  useEffect(() => {
    if (activeDocumentId && tabsContainerRef.current) {
      const activeTab = tabsContainerRef.current.querySelector(`.${styles.activeTab}`);
      if (activeTab) {
        activeTab.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
      }
    }
  }, [activeDocumentId]);

  return (
    <div className={styles.tabs} ref={tabsContainerRef}>
      {documents.map((doc) => {
        const docId = doc.metadata.document_id;
        const isActive = docId === activeDocumentId;
        const hasUnsaved = unsavedChanges.get(docId) || false;
        const isDeleted = doc.metadata.deleted || false;

        return (
          <div
            key={docId}
            className={classNames(styles.tab, {
              [styles.activeTab]: isActive,
              [styles.unsavedTab]: hasUnsaved,
              [styles.deletedTab]: isDeleted,
            })}
            onClick={() => onSelectDocument(docId)}
          >
            <span className={styles.tabName}>
              {hasUnsaved && <span className={styles.unsavedIndicator}>•</span>}
              {doc.metadata.name}
              {isDeleted && <span className="deleted-indicator">DELETED</span>}
            </span>
            <div className={styles.tabActions}>
              <button
                className={styles.closeTab}
                onClick={(e) => {
                  e.stopPropagation();
                  console.log('Closing document:', docId, 'isDeleted:', isDeleted);
                  onCloseDocument(docId);
                }}
                title="Close tab"
                aria-label="Close tab"
              >
                <X size={16} />
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
};