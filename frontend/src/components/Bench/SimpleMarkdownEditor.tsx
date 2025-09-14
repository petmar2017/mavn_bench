import React, { useState, useEffect } from 'react';
import { Save, Edit, Eye } from 'lucide-react';
import classNames from 'classnames';
import { documentApi } from '../../services/api';
import styles from './SimpleMarkdownEditor.module.css';

interface SimpleMarkdownEditorProps {
  documentId: string;
  content: string;
  contentType: 'summary' | 'content' | 'transcript' | 'extracted';
  label?: string;
  onSave?: (newContent: string) => void;
  className?: string;
}

export const SimpleMarkdownEditor: React.FC<SimpleMarkdownEditorProps> = ({
  documentId,
  content: initialContent,
  contentType,
  label,
  onSave,
  className
}) => {
  const [content, setContent] = useState(initialContent || '');
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setContent(initialContent || '');
    setHasChanges(false);
  }, [initialContent]);

  const handleSave = async () => {
    if (!hasChanges) return;

    setIsSaving(true);
    setError(null);

    try {
      // Update the document content based on type
      const updateData = contentType === 'summary'
        ? { metadata: { summary: content } }
        : { content: content };

      await documentApi.updateDocument(documentId, updateData);

      setHasChanges(false);
      setIsEditing(false);
      onSave?.(content);
    } catch (err: any) {
      console.error(`Failed to save ${contentType}:`, err);
      setError(`Failed to save ${contentType}. Please try again.`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    setContent(initialContent || '');
    setHasChanges(false);
    setIsEditing(false);
    setError(null);
  };

  const handleChange = (value: string) => {
    setContent(value);
    setHasChanges(value !== initialContent);
    setError(null);
  };

  const renderMarkdown = (text: string): string => {
    // Basic markdown rendering
    let html = text;

    // Headers
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

    // Bold
    html = html.replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>');
    html = html.replace(/__(.*?)__/gim, '<strong>$1</strong>');

    // Italic
    html = html.replace(/\*(.*?)\*/gim, '<em>$1</em>');
    html = html.replace(/_(.*?)_/gim, '<em>$1</em>');

    // Links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/gim, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

    // Code blocks
    html = html.replace(/```([^`]+)```/gim, '<pre><code>$1</code></pre>');
    html = html.replace(/`([^`]+)`/gim, '<code>$1</code>');

    // Lists
    html = html.replace(/^\* (.+)$/gim, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

    // Line breaks
    html = html.replace(/\n\n/gim, '</p><p>');
    html = html.replace(/\n/gim, '<br />');
    html = `<p>${html}</p>`;

    return html;
  };

  return (
    <div className={classNames(styles.summaryEditor, className)}>
      <div className={styles.toolbar}>
        <div className={styles.title}>Document Summary</div>
        <div className={styles.actions}>
          {!isEditing ? (
            <button
              className={styles.editButton}
              onClick={() => setIsEditing(true)}
              title="Edit summary"
            >
              <Edit size={16} />
              Edit
            </button>
          ) : (
            <>
              <button
                className={styles.cancelButton}
                onClick={handleCancel}
                disabled={isSaving}
              >
                Cancel
              </button>
              <button
                className={classNames(styles.saveButton, {
                  [styles.disabled]: !hasChanges || isSaving
                })}
                onClick={handleSave}
                disabled={!hasChanges || isSaving}
              >
                <Save size={16} />
                {isSaving ? 'Saving...' : 'Save'}
              </button>
            </>
          )}
        </div>
      </div>

      {error && (
        <div className={styles.error}>
          {error}
        </div>
      )}

      <div className={styles.content}>
        {isEditing ? (
          <textarea
            className={styles.editor}
            value={content}
            onChange={(e) => handleChange(e.target.value)}
            placeholder={`Enter ${contentType} here...`}
            disabled={isSaving}
          />
        ) : (
          <div className={styles.preview}>
            {content ? (
              <div
                className={styles.markdownContent}
                dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
              />
            ) : (
              <div className={styles.placeholder}>
                No {contentType} available. Click Edit to add content.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};