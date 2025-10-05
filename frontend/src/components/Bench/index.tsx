import { useState, useEffect, forwardRef, useImperativeHandle, useRef } from 'react';
import { X, Save, Maximize2, Minimize2, ChevronRight, ChevronLeft } from 'lucide-react';
import classNames from 'classnames';
import { DocumentBench, type DocumentBenchRef } from './DocumentBench';
import { DocumentTabs } from './DocumentTabs';
import { ToolsMenu } from '../ToolsMenu/ToolsMenu';
import { documentApi } from '../../services/api';
import type { DocumentMessage, DocumentMetadata } from '../../types/document';
import { logger } from '../../services/logging';
import styles from './Bench.module.css';

interface BenchProps {
  selectedDocumentMetadata: DocumentMetadata | null;
  onClose?: () => void;
  onHistoryClick?: (documentId: string) => void;
}

export interface BenchRef {
  closeDocument: (documentId: string) => void;
}

export const Bench = forwardRef<BenchRef, BenchProps>(({ selectedDocumentMetadata, onClose, onHistoryClick }, ref) => {
  logger.debug('Bench component render', { selectedDocumentMetadata });
  const [openDocuments, setOpenDocuments] = useState<DocumentMessage[]>([]);
  const [activeDocumentId, setActiveDocumentId] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [unsavedChanges, setUnsavedChanges] = useState<Map<string, boolean>>(new Map());
  const [showToolsPanel, setShowToolsPanel] = useState(true);
  const documentBenchRef = useRef<DocumentBenchRef>(null);

  // Define handleCloseDocument before useImperativeHandle
  const handleCloseDocument = (documentId: string) => {
    logger.info('handleCloseDocument called', { documentId });
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

  // Expose closeDocument method to parent component
  useImperativeHandle(ref, () => ({
    closeDocument: handleCloseDocument
  }), [openDocuments, activeDocumentId]);

  // Fetch and add selected document to open documents if not already open
  useEffect(() => {
    logger.debug('Bench useEffect triggered', { selectedDocumentMetadata });
    if (selectedDocumentMetadata) {
      const docId = selectedDocumentMetadata.document_id;
      logger.debug('Processing document', { documentId: docId });
      const isOpen = openDocuments.some(doc => doc.metadata.document_id === docId);
      logger.debug('Document open status', { documentId: docId, isOpen });

      if (!isOpen) {
        // Fetch the full document
        const fetchDocument = async () => {
          try {
            const fullDocument = await documentApi.getDocument(docId);
            setOpenDocuments(prev => [...prev, fullDocument]);
            logger.info('Fetched and added document to open documents', { documentId: docId });
          } catch (error) {
            logger.error('Failed to fetch document', { documentId: docId, error });
          }
        };
        fetchDocument();
      }
      setActiveDocumentId(docId);
      logger.debug('Set active document', { documentId: docId });
    }
  }, [selectedDocumentMetadata]);

  const handleSaveDocument = async (documentId: string) => {
    try {
      // Call the save function from the document editor
      if (documentBenchRef.current) {
        await documentBenchRef.current.save();
        logger.info('Document saved successfully', { documentId });

        // Clear unsaved changes after successful save
        setUnsavedChanges(prev => {
          const newMap = new Map(prev);
          newMap.set(documentId, false);
          return newMap;
        });
      }
    } catch (error) {
      logger.error('Failed to save document', { documentId, error });
    }
  };

  const handleDocumentChange = (documentId: string) => {
    setUnsavedChanges(prev => {
      const newMap = new Map(prev);
      newMap.set(documentId, true);
      return newMap;
    });
  };

  const handleDeleteDocument = async (documentId: string, isHardDelete: boolean) => {
    try {
      if (isHardDelete) {
        // Permanent delete
        await documentApi.deleteDocument(documentId, { params: { soft_delete: false } });
        logger.info('Document permanently deleted', { documentId });
      } else {
        // Soft delete
        await documentApi.deleteDocument(documentId);
        logger.info('Document soft deleted', { documentId });
      }

      // Always close the document tab after deletion (both soft and hard delete)
      handleCloseDocument(documentId);
    } catch (error) {
      logger.error('Failed to delete document', { documentId, error });
    }
  };

  const activeDocument = openDocuments.find(doc => doc.metadata.document_id === activeDocumentId);

  const handleToolExecuted = async (toolId: string, result: any) => {
    logger.info('Tool executed successfully', { toolId, documentId: activeDocumentId });

    // Refresh the active document to get updated tools array
    if (activeDocumentId) {
      try {
        const updatedDoc = await documentApi.getDocument(activeDocumentId);
        setOpenDocuments(prev =>
          prev.map(doc =>
            doc.metadata.document_id === activeDocumentId ? updatedDoc : doc
          )
        );
      } catch (error) {
        logger.error('Failed to refresh document after tool execution', { error });
      }
    }
  };

  const handleToolError = (toolId: string, error: Error) => {
    logger.error('Tool execution failed', { toolId, error: error.message });
  };

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
          onDeleteDocument={handleDeleteDocument}
        />

        <div className={styles.benchActions}>
          {activeDocument && unsavedChanges.get(activeDocumentId!) && !activeDocument.metadata.deleted && (
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
            onClick={() => setShowToolsPanel(!showToolsPanel)}
            title={showToolsPanel ? 'Hide tools panel' : 'Show tools panel'}
          >
            {showToolsPanel ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
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

      <div className={styles.benchLayout}>
        <div className={styles.benchContent}>
          {activeDocument && (
            <DocumentBench
              ref={documentBenchRef}
              document={activeDocument}
              onDocumentChange={() => handleDocumentChange(activeDocumentId!)}
              onDelete={() => {
                const isDeleted = activeDocument.metadata.deleted;
                const isHardDelete = isDeleted;
                if (isHardDelete && !confirm('Permanently delete this document? This cannot be undone.')) {
                  return;
                }
                handleDeleteDocument(activeDocumentId!, isHardDelete);
              }}
              onDownload={() => logger.info('Download clicked')}
              onHistory={() => {
                if (activeDocumentId && onHistoryClick) {
                  onHistoryClick(activeDocumentId);
                  logger.info('Version history clicked', { documentId: activeDocumentId });
                }
              }}
            />
          )}
        </div>

        {showToolsPanel && activeDocument && (
          <div className={styles.toolsPanel}>
            <ToolsMenu
              document={activeDocument}
              onToolExecuted={handleToolExecuted}
              onToolError={handleToolError}
            />
          </div>
        )}
      </div>
    </div>
  );
});

Bench.displayName = 'Bench';