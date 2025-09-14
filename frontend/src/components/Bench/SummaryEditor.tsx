import React, { useState, useEffect } from 'react';
import { Save, Edit, Eye } from 'lucide-react';
import classNames from 'classnames';
import { documentApi } from '../../services/api';
import styles from './SummaryEditor.module.css';

interface SummaryEditorProps {
  documentId: string;
  summary: string;
  onSave?: (newSummary: string) => void;
  className?: string;
}

export const SummaryEditor: React.FC<SummaryEditorProps> = ({
  documentId,
  summary: initialSummary,
  onSave,
  className
}) => {
  const [summary, setSummary] = useState(initialSummary || '');
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setSummary(initialSummary || '');
    setHasChanges(false);
  }, [initialSummary]);

  const handleSave = async () => {
    if (!hasChanges) return;

    setIsSaving(true);
    setError(null);

    try {
      // Update the document summary
      await documentApi.updateDocument(documentId, {
        metadata: {
          summary: summary
        }
      });

      setHasChanges(false);
      setIsEditing(false);
      onSave?.(summary);
    } catch (err: any) {
      console.error('Failed to save summary:', err);
      setError('Failed to save summary. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    setSummary(initialSummary || '');
    setHasChanges(false);
    setIsEditing(false);
    setError(null);
  };

  const handleChange = (value: string) => {
    setSummary(value);
    setHasChanges(value !== initialSummary);
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
            value={summary}
            onChange={(e) => handleChange(e.target.value)}
            placeholder="Enter a summary for this document..."
            disabled={isSaving}
          />
        ) : (
          <div className={styles.preview}>
            {summary ? (
              <div
                className={styles.markdownContent}
                dangerouslySetInnerHTML={{ __html: renderMarkdown(summary) }}
              />
            ) : (
              <div className={styles.placeholder}>
                No summary available. Click Edit to add one.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};