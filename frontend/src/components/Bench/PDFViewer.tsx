import { useState, useEffect, useCallback, forwardRef, useImperativeHandle } from 'react';
import { FileText, Loader, CheckCircle, FileType, FileBarChart } from 'lucide-react';
import type { DocumentMessage } from '../../services/api';
import { documentApi } from '../../services/api';
import { documentContentService } from '../../services/documentContent';
import { logger } from '../../services/logging';
import { ViewerTabBar } from './ViewerTabBar';
import type { ViewerTab } from './ViewerTabBar';
import { ViewerToolbar } from './ViewerToolbar';
import { SimpleMarkdownEditor } from './SimpleMarkdownEditor';
import styles from './PDFViewer.module.css';

interface PDFViewerProps {
  document: DocumentMessage;
  onContentChange?: () => void;
  onDelete?: () => void;
  onDownload?: () => void;
  onHistory?: () => void;
}

export interface PDFViewerRef {
  save: () => Promise<void>;
  hasUnsavedChanges: () => boolean;
}

type ViewMode = 'summary' | 'transcript' | 'original';

export const PDFViewer = forwardRef<PDFViewerRef, PDFViewerProps>(
  ({ document, onContentChange, onDelete, onDownload, onHistory }, ref) => {
    const [viewMode, setViewMode] = useState<ViewMode>('summary');
    const [transcript, setTranscript] = useState('');
    const [originalTranscript, setOriginalTranscript] = useState('');
    const [summary, setSummary] = useState('');
    const [originalSummary, setOriginalSummary] = useState('');
    const [originalPdfUrl, setOriginalPdfUrl] = useState<string | null>(null);
    const [isModified, setIsModified] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [saveSuccess, setSaveSuccess] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Load document content
    useEffect(() => {
      const loadContent = async () => {
        setIsLoading(true);
        setError(null);

        try {
          const documentId = document.metadata.document_id;
          const contentData = await documentContentService.getContent(documentId);

          // Load transcript (markdown converted from PDF)
          const transcriptContent = contentData.formatted_content || contentData.text || contentData.raw_text || '';
          setTranscript(transcriptContent);
          setOriginalTranscript(transcriptContent);

          // Load summary if available
          const summaryContent = contentData.summary || '';
          setSummary(summaryContent);
          setOriginalSummary(summaryContent);

          // Load original PDF URL if file_path exists
          if (document.metadata.file_path) {
            const pdfUrl = `${import.meta.env.VITE_API_URL}/documents/${documentId}/file`;
            setOriginalPdfUrl(pdfUrl);
            logger.info('Original PDF available', { documentId, pdfUrl });
          } else {
            setOriginalPdfUrl(null);
            logger.info('No original PDF file available', { documentId });
          }

          setIsModified(false);
          logger.info('Loaded PDF document content', { documentId });
        } catch (err) {
          logger.error('Failed to load PDF content', { error: err });
          setError('Failed to load PDF content');
        } finally {
          setIsLoading(false);
        }
      };

      loadContent();
    }, [document]);

    // Handle content changes
    const handleTranscriptChange = useCallback((value: string) => {
      setTranscript(value);
      const hasChanges = value !== originalTranscript || summary !== originalSummary;
      setIsModified(hasChanges);
      if (hasChanges) {
        onContentChange?.();
      }
    }, [originalTranscript, originalSummary, summary, onContentChange]);


    // Save document with version history
    const handleSave = async () => {
      if (!isModified) return;

      setIsSaving(true);
      setError(null);

      try {
        const documentId = document.metadata.document_id;

        // Create update request with the appropriate content based on what changed
        const updateRequest: any = {};

        // Save transcript as formatted_content
        if (transcript !== originalTranscript) {
          updateRequest.content = transcript;
        }

        // Save summary
        if (summary !== originalSummary) {
          updateRequest.summary = summary;
        }

        await documentApi.updateDocument(documentId, updateRequest);

        // Clear the content cache to force reload
        documentContentService.clearCache(documentId);

        // Update original values
        setOriginalTranscript(transcript);
        setOriginalSummary(summary);
        setIsModified(false);
        setSaveSuccess(true);

        logger.info('PDF document saved successfully', { documentId });

        // Hide success message after 3 seconds
        setTimeout(() => setSaveSuccess(false), 3000);
      } catch (err) {
        logger.error('Failed to save PDF document', { error: err });
        setError('Failed to save document. Please try again.');
      } finally {
        setIsSaving(false);
      }
    };

    // Expose save function and state to parent component
    useImperativeHandle(ref, () => ({
      save: handleSave,
      hasUnsavedChanges: () => isModified
    }), [handleSave, isModified]);

    // Handle keyboard shortcuts
    useEffect(() => {
      const handleKeyDown = (e: KeyboardEvent) => {
        // Ctrl/Cmd + S to save
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
          e.preventDefault();
          if (isModified && !isSaving) {
            handleSave();
          }
        }
      };

      window.addEventListener('keydown', handleKeyDown);
      return () => window.removeEventListener('keydown', handleKeyDown);
    }, [isModified, isSaving]);

    // Render loading state
    if (isLoading) {
      return (
        <div className={styles.pdfViewer}>
          <div className={styles.loadingContainer}>
            <Loader size={32} className={styles.spinner} />
            <p>Loading PDF content...</p>
          </div>
        </div>
      );
    }

    // Render error state
    if (error && !transcript && !summary) {
      return (
        <div className={styles.pdfViewer}>
          <div className={styles.errorContainer}>
            <p className={styles.errorMessage}>{error}</p>
          </div>
        </div>
      );
    }

    const tabs: ViewerTab[] = [
      { id: 'summary', label: 'Summary', icon: <FileBarChart size={16} /> },
      { id: 'transcript', label: 'Transcript', icon: <FileType size={16} /> },
      { id: 'original', label: 'Original', icon: <FileText size={16} /> },
    ];

    return (
      <div className={styles.pdfViewer}>
        <ViewerTabBar
          tabs={tabs}
          activeTab={viewMode}
          onTabChange={(tabId) => setViewMode(tabId as ViewMode)}
        />
        <ViewerToolbar
          documentId={document.metadata.document_id}
          isDeleted={document.metadata.deleted}
          onDelete={onDelete}
          onDownload={onDownload}
          onHistory={onHistory}
        >
          {saveSuccess && (
            <span className={styles.saveSuccess}>
              <CheckCircle size={16} />
              Saved
            </span>
          )}
        </ViewerToolbar>

        <div className={styles.editorContainer}>
          {viewMode === 'transcript' && (
            <SimpleMarkdownEditor
              documentId={document.metadata.document_id}
              content={transcript}
              contentType="transcript"
              label="Document Transcript"
              onSave={(newTranscript) => {
                setTranscript(newTranscript);
                setOriginalTranscript(newTranscript);
                setIsModified(false);
                setSaveSuccess(true);
                setTimeout(() => setSaveSuccess(false), 3000);
              }}
            />
          )}

          {viewMode === 'original' && (
            <div className={styles.previewPane}>
              {originalPdfUrl ? (
                <iframe
                  src={originalPdfUrl}
                  className={styles.pdfEmbed}
                  title="Original PDF"
                />
              ) : (
                <div className={styles.emptyState}>
                  <FileText size={48} />
                  <h3>Original PDF View</h3>
                  <p>The original PDF display is not yet available.</p>
                  <p className={styles.hint}>
                    Use the Transcript view to see the extracted text content.
                  </p>
                </div>
              )}
            </div>
          )}

          {viewMode === 'summary' && (
            <SimpleMarkdownEditor
              documentId={document.metadata.document_id}
              content={summary}
              contentType="summary"
              label="Document Summary"
              onSave={(newSummary) => {
                setSummary(newSummary);
                setOriginalSummary(newSummary);
                setIsModified(false);
                setSaveSuccess(true);
                setTimeout(() => setSaveSuccess(false), 3000);
              }}
            />
          )}
        </div>

        {error && (
          <div className={styles.errorBar}>
            <span className={styles.errorText}>{error}</span>
          </div>
        )}
      </div>
    );
  }
);

PDFViewer.displayName = 'PDFViewer';