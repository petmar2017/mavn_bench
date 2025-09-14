import { useState, useEffect, useCallback, forwardRef, useImperativeHandle } from 'react';
import { Edit, Eye, Loader, CheckCircle } from 'lucide-react';
import classNames from 'classnames';
import type { DocumentMessage } from '../../services/api';
import { documentApi } from '../../services/api';
import { documentContentService } from '../../services/documentContent';
import { logger } from '../../services/logging';
import styles from './TextEditor.module.css';

interface TextEditorProps {
  document: DocumentMessage;
  onContentChange?: () => void;
  viewMode?: 'edit' | 'preview';
}

export interface TextEditorRef {
  save: () => Promise<void>;
  hasUnsavedChanges: () => boolean;
}

export const TextEditor = forwardRef<TextEditorRef, TextEditorProps>((
  { document, onContentChange, viewMode: initialViewMode },
  ref
) => {
  const [content, setContent] = useState('');
  const [originalContent, setOriginalContent] = useState('');
  const [viewMode, setViewMode] = useState<'edit' | 'preview'>(initialViewMode || 'edit');
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
        const text = contentData.text || contentData.formatted_content || contentData.raw_text || '';
        setContent(text);
        setOriginalContent(text);
        setIsModified(false);
        logger.info('Loaded text document content', { documentId });
      } catch (err) {
        logger.error('Failed to load text document content', { error: err });
        setError('Failed to load document content');
        setContent('');
        setOriginalContent('');
      } finally {
        setIsLoading(false);
      }
    };

    loadContent();
  }, [document]);

  // Handle content changes
  const handleContentChange = useCallback((value: string) => {
    setContent(value);
    setIsModified(value !== originalContent);
    onContentChange?.();
  }, [originalContent, onContentChange]);

  // Save document with version history
  const handleSave = async () => {
    if (!isModified) return;

    setIsSaving(true);
    setError(null);

    try {
      const documentId = document.metadata.document_id;

      // Create update request with only the content field
      const updateRequest = {
        content: content
      };

      await documentApi.updateDocument(documentId, updateRequest);

      // Clear the content cache to force reload
      documentContentService.clearCache(documentId);

      setOriginalContent(content);
      setIsModified(false);
      setSaveSuccess(true);

      logger.info('Text document saved successfully', { documentId });

      // Hide success message after 3 seconds
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      logger.error('Failed to save text document', { error: err });
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
      // Ctrl/Cmd + E to toggle edit mode
      if ((e.ctrlKey || e.metaKey) && e.key === 'e') {
        e.preventDefault();
        setViewMode(viewMode === 'edit' ? 'preview' : 'edit');
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isModified, isSaving, viewMode]);

  // Render loading state
  if (isLoading) {
    return (
      <div className={styles.markdownEditor}>
        <div className={styles.loadingContainer}>
          <Loader size={32} className={styles.spinner} />
          <p>Loading document content...</p>
        </div>
      </div>
    );
  }

  // Render error state
  if (error && !content) {
    return (
      <div className={styles.markdownEditor}>
        <div className={styles.errorContainer}>
          <p className={styles.errorMessage}>{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.markdownEditor}>
      <div className={styles.editorToolbar}>
        <div className={styles.viewModeButtons}>
          <button
            className={classNames(styles.modeButton, {
              [styles.active]: viewMode === 'edit',
            })}
            onClick={() => setViewMode('edit')}
            title="Edit mode (Ctrl+E)"
          >
            <Edit size={16} />
            Edit
          </button>
          <button
            className={classNames(styles.modeButton, {
              [styles.active]: viewMode === 'preview',
            })}
            onClick={() => setViewMode('preview')}
            title="Preview mode (Ctrl+E)"
          >
            <Eye size={16} />
            Preview
          </button>
        </div>

        <div className={styles.editorActions}>
          {saveSuccess && (
            <span className={styles.saveSuccess}>
              <CheckCircle size={16} />
              Saved
            </span>
          )}
        </div>
      </div>

      <div className={classNames(styles.editorContainer, styles[viewMode])}>
        {viewMode === 'edit' && (
          <div className={styles.editorPane}>
            <textarea
              className={styles.editorTextarea}
              value={content}
              onChange={(e) => handleContentChange(e.target.value)}
              placeholder="Enter your text here..."
              spellCheck={true}
            />
          </div>
        )}

        {viewMode === 'preview' && (
          <div className={styles.previewPane}>
            <div className={styles.textPreview}>
              <pre>{content || 'No content to preview'}</pre>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className={styles.errorBar}>
          <span className={styles.errorText}>{error}</span>
        </div>
      )}
    </div>
  );
});

TextEditor.displayName = 'TextEditor';