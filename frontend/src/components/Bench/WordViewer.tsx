import { useState, useEffect, useCallback, forwardRef, useImperativeHandle } from 'react';
import { FileText, Loader, CheckCircle, FileType, FileBarChart } from 'lucide-react';
import classNames from 'classnames';
import type { DocumentMessage } from '../../services/api';
import { documentApi } from '../../services/api';
import { documentContentService } from '../../services/documentContent';
import { logger } from '../../services/logging';
import { ViewerTabBar } from './ViewerTabBar';
import type { ViewerTab } from './ViewerTabBar';
import { SummaryEditor } from './SummaryEditor';
import { MarkdownContentEditor } from './MarkdownContentEditor';
import styles from './WordViewer.module.css';

interface WordViewerProps {
  document: DocumentMessage;
  onContentChange?: () => void;
}

export interface WordViewerRef {
  save: () => Promise<void>;
  hasUnsavedChanges: () => boolean;
}

type ViewMode = 'summary' | 'extracted' | 'original';

export const WordViewer = forwardRef<WordViewerRef, WordViewerProps>(
  ({ document, onContentChange }, ref) => {
    const [viewMode, setViewMode] = useState<ViewMode>('summary');
    const [extractedText, setExtractedText] = useState('');
    const [originalExtractedText, setOriginalExtractedText] = useState('');
    const [summary, setSummary] = useState('');
    const [originalSummary, setOriginalSummary] = useState('');
    const [originalContent, setOriginalContent] = useState('');
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

          // Load extracted text (markdown converted from Word doc)
          const extracted = contentData.formatted_content || contentData.text || contentData.raw_text || '';
          setExtractedText(extracted);
          setOriginalExtractedText(extracted);

          // Load summary if available
          const summaryContent = contentData.summary || '';
          setSummary(summaryContent);
          setOriginalSummary(summaryContent);

          // For original view, show the raw text if available
          setOriginalContent(contentData.raw_text || extracted);

          setIsModified(false);
          logger.info('Loaded Word document content', { documentId });
        } catch (err) {
          logger.error('Failed to load Word content', { error: err });
          setError('Failed to load Word document content');
        } finally {
          setIsLoading(false);
        }
      };

      loadContent();
    }, [document]);

    // Handle content changes
    const handleExtractedTextChange = useCallback((value: string) => {
      setExtractedText(value);
      const hasChanges = value !== originalExtractedText || summary !== originalSummary;
      setIsModified(hasChanges);
      if (hasChanges) {
        onContentChange?.();
      }
    }, [originalExtractedText, originalSummary, summary, onContentChange]);


    // Save document with version history
    const handleSave = async () => {
      if (!isModified) return;

      setIsSaving(true);
      setError(null);

      try {
        const documentId = document.metadata.document_id;

        // Create update request with the appropriate content based on what changed
        const updateRequest: any = {};

        // Save extracted text as formatted_content
        if (extractedText !== originalExtractedText) {
          updateRequest.content = extractedText;
        }

        // Save summary
        if (summary !== originalSummary) {
          updateRequest.summary = summary;
        }

        await documentApi.updateDocument(documentId, updateRequest);

        // Clear the content cache to force reload
        documentContentService.clearCache(documentId);

        // Update original values
        setOriginalExtractedText(extractedText);
        setOriginalSummary(summary);
        setIsModified(false);
        setSaveSuccess(true);

        logger.info('Word document saved successfully', { documentId });

        // Hide success message after 3 seconds
        setTimeout(() => setSaveSuccess(false), 3000);
      } catch (err) {
        logger.error('Failed to save Word document', { error: err });
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
        <div className={styles.wordViewer}>
          <div className={styles.loadingContainer}>
            <Loader size={32} className={styles.spinner} />
            <p>Loading Word document content...</p>
          </div>
        </div>
      );
    }

    // Render error state
    if (error && !extractedText && !summary) {
      return (
        <div className={styles.wordViewer}>
          <div className={styles.errorContainer}>
            <p className={styles.errorMessage}>{error}</p>
          </div>
        </div>
      );
    }

    const tabs: ViewerTab[] = [
      { id: 'summary', label: 'Summary', icon: <FileBarChart size={16} /> },
      { id: 'extracted', label: 'Extracted', icon: <FileType size={16} /> },
      { id: 'original', label: 'Original', icon: <FileText size={16} /> },
    ];

    return (
      <div className={styles.wordViewer}>
        <ViewerTabBar
          tabs={tabs}
          activeTab={viewMode}
          onTabChange={(tabId) => setViewMode(tabId as ViewMode)}
        />
        <div className={styles.editorToolbar}>

          <div className={styles.editorActions}>
            {saveSuccess && (
              <span className={styles.saveSuccess}>
                <CheckCircle size={16} />
                Saved
              </span>
            )}
          </div>
        </div>

        <div className={styles.editorContainer}>
          {viewMode === 'extracted' && (
            <MarkdownContentEditor
              content={extractedText}
              onChange={handleExtractedTextChange}
              isModified={isModified}
            />
          )}

          {viewMode === 'original' && (
            <div className={styles.previewPane}>
              {originalContent ? (
                <pre className={styles.originalContent}>{originalContent}</pre>
              ) : (
                <div className={styles.emptyState}>
                  <FileText size={48} />
                  <h3>Original Content</h3>
                  <p>No original content available.</p>
                  <p className={styles.hint}>
                    Use the Extracted view to see the processed text content.
                  </p>
                </div>
              )}
            </div>
          )}

          {viewMode === 'summary' && (
            <SummaryEditor
              documentId={document.metadata.document_id}
              summary={summary}
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

WordViewer.displayName = 'WordViewer';