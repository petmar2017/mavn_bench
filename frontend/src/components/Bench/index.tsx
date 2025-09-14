import { useState, useEffect } from 'react';
import { X, Save, Download, History, Maximize2, Minimize2 } from 'lucide-react';
import classNames from 'classnames';
import { DocumentBench } from './DocumentBench';
import { DocumentTabs } from './DocumentTabs';
import type { DocumentMessage } from '../../services/api';
import styles from './Bench.module.css';

interface BenchProps {
  selectedDocument: DocumentMessage | null;
  onClose?: () => void;
}

export const Bench: React.FC<BenchProps> = ({ selectedDocument, onClose }) => {
  const [openDocuments, setOpenDocuments] = useState<DocumentMessage[]>([]);
  const [activeDocumentId, setActiveDocumentId] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [unsavedChanges, setUnsavedChanges] = useState<Map<string, boolean>>(new Map());

  // Add selected document to open documents if not already open
  useEffect(() => {
    if (selectedDocument && selectedDocument.metadata) {
      const docId = selectedDocument.metadata.document_id;
      const isOpen = openDocuments.some(doc => doc.metadata.document_id === docId);

      if (!isOpen) {
        setOpenDocuments(prev => [...prev, selectedDocument]);
      }
      setActiveDocumentId(docId);
    }
  }, [selectedDocument]);

  const handleCloseDocument = (documentId: string) => {
    setOpenDocuments(prev => prev.filter(doc => doc.metadata.document_id !== documentId));

    // If closing the active document, switch to another one
    if (activeDocumentId === documentId) {
      const remainingDocs = openDocuments.filter(doc => doc.metadata.document_id !== documentId);
      if (remainingDocs.length > 0) {
        setActiveDocumentId(remainingDocs[0].metadata.document_id);
      } else {
        setActiveDocumentId(null);
      }
    }

    // Clear unsaved changes for this document
    setUnsavedChanges(prev => {
      const newMap = new Map(prev);
      newMap.delete(documentId);
      return newMap;
    });
  };

  const handleSaveDocument = async (documentId: string) => {
    // TODO: Implement save functionality
    console.log('Saving document:', documentId);
    setUnsavedChanges(prev => {
      const newMap = new Map(prev);
      newMap.set(documentId, false);
      return newMap;
    });
  };

  const handleDocumentChange = (documentId: string) => {
    setUnsavedChanges(prev => {
      const newMap = new Map(prev);
      newMap.set(documentId, true);
      return newMap;
    });
  };

  const activeDocument = openDocuments.find(doc => doc.metadata.document_id === activeDocumentId);

  if (openDocuments.length === 0) {
    return (
      <div className={styles.emptyBench}>
        <div className={styles.emptyMessage}>
          <h3>No Document Selected</h3>
          <p>Select a document from the left panel to view or edit it here</p>
        </div>
      </div>
    );
  }

  return (
    <div className={classNames(styles.bench, { [styles.fullscreen]: isFullscreen })}>
      <div className={styles.benchHeader}>
        <DocumentTabs
          documents={openDocuments}
          activeDocumentId={activeDocumentId}
          unsavedChanges={unsavedChanges}
          onSelectDocument={setActiveDocumentId}
          onCloseDocument={handleCloseDocument}
        />

        <div className={styles.benchActions}>
          {activeDocument && unsavedChanges.get(activeDocumentId!) && (
            <button
              className={styles.actionButton}
              onClick={() => handleSaveDocument(activeDocumentId!)}
              title="Save document"
            >
              <Save size={18} />
            </button>
          )}

          <button
            className={styles.actionButton}
            onClick={() => console.log('Download')}
            title="Download document"
          >
            <Download size={18} />
          </button>

          <button
            className={styles.actionButton}
            onClick={() => console.log('Version history')}
            title="Version history"
          >
            <History size={18} />
          </button>

          <button
            className={styles.actionButton}
            onClick={() => setIsFullscreen(!isFullscreen)}
            title={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
          >
            {isFullscreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
          </button>
        </div>
      </div>

      <div className={styles.benchContent}>
        {activeDocument && (
          <DocumentBench
            document={activeDocument}
            onDocumentChange={() => handleDocumentChange(activeDocumentId!)}
          />
        )}
      </div>
    </div>
  );
};