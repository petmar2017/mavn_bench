import { useState, useEffect } from 'react';
import { Eye, Edit, Save, Loader } from 'lucide-react';
import classNames from 'classnames';
import type { DocumentMessage } from '../../services/api';
import { documentContentService } from '../../services/documentContent';
import styles from './MarkdownEditor.module.css';

interface MarkdownEditorProps {
  document: DocumentMessage;
  onContentChange?: () => void;
  viewMode?: 'edit' | 'preview' | 'split';
}

export const MarkdownEditor: React.FC<MarkdownEditorProps> = ({
  document,
  onContentChange,
  viewMode: initialViewMode,
}) => {
  const [content, setContent] = useState('');
  const [viewMode, setViewMode] = useState<'edit' | 'preview' | 'split'>(initialViewMode || 'split');
  const [isModified, setIsModified] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Fetch document content on-demand
    const loadContent = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const documentId = document.metadata.document_id;
        const contentData = await documentContentService.getContent(documentId);
        const text = contentData.text || contentData.formatted_content || contentData.raw_text || '';
        setContent(text);
        setIsModified(false);
      } catch (err) {
        console.error('Failed to load document content:', err);
        setError('Failed to load document content');
        setContent('');
      } finally {
        setIsLoading(false);
      }
    };

    loadContent();
  }, [document]);

  const handleContentChange = (value: string) => {
    setContent(value);
    setIsModified(true);
    onContentChange?.();
  };

  const renderMarkdown = (markdown: string): string => {
    // Basic markdown rendering (replace with proper markdown library like marked or react-markdown)
    let html = markdown;

    // Headers
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

    // Bold
    html = html.replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>');
    html = html.replace(/__(.*?)__/gim, '<strong>$1</strong>');

    // Italic
    html = html.replace(/\*(.*)\*/gim, '<em>$1</em>');
    html = html.replace(/_(.*?)_/gim, '<em>$1</em>');

    // Links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/gim, '<a href="$2">$1</a>');

    // Code blocks
    html = html.replace(/```([^`]+)```/gim, '<pre><code>$1</code></pre>');
    html = html.replace(/`([^`]+)`/gim, '<code>$1</code>');

    // Lists
    html = html.replace(/^\* (.+)$/gim, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

    // Line breaks
    html = html.replace(/\n/gim, '<br />');

    return html;
  };

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

  if (error) {
    return (
      <div className={styles.markdownEditor}>
        <div className={styles.errorContainer}>
          <p className={styles.errorMessage}>{error}</p>
          <button
            className={styles.retryButton}
            onClick={() => window.location.reload()}
          >
            Retry
          </button>
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
            title="Edit mode"
          >
            <Edit size={16} />
            Edit
          </button>
          <button
            className={classNames(styles.modeButton, {
              [styles.active]: viewMode === 'split',
            })}
            onClick={() => setViewMode('split')}
            title="Split view"
          >
            Split
          </button>
          <button
            className={classNames(styles.modeButton, {
              [styles.active]: viewMode === 'preview',
            })}
            onClick={() => setViewMode('preview')}
            title="Preview mode"
          >
            <Eye size={16} />
            Preview
          </button>
        </div>

        {isModified && (
          <span className={styles.modifiedIndicator}>Modified</span>
        )}
      </div>

      <div className={classNames(styles.editorContainer, styles[viewMode])}>
        {(viewMode === 'edit' || viewMode === 'split') && (
          <div className={styles.editorPane}>
            <textarea
              className={styles.editorTextarea}
              value={content}
              onChange={(e) => handleContentChange(e.target.value)}
              placeholder="Enter markdown content..."
              spellCheck={false}
            />
          </div>
        )}

        {(viewMode === 'preview' || viewMode === 'split') && (
          <div className={styles.previewPane}>
            <div
              className={styles.markdownPreview}
              dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
            />
          </div>
        )}
      </div>
    </div>
  );
};