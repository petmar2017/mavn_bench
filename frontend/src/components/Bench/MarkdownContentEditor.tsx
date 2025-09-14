import React, { useState } from 'react';
import { Eye, Edit, Columns } from 'lucide-react';
import classNames from 'classnames';
import styles from './MarkdownContentEditor.module.css';

interface MarkdownContentEditorProps {
  content: string;
  onChange: (value: string) => void;
  isModified?: boolean;
}

export const MarkdownContentEditor: React.FC<MarkdownContentEditorProps> = ({
  content,
  onChange,
  isModified = false
}) => {
  const [viewMode, setViewMode] = useState<'edit' | 'preview' | 'split'>('split');

  const renderMarkdown = (markdown: string): string => {
    // Basic markdown rendering
    let html = markdown;

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
    <div className={styles.contentEditor}>
      <div className={styles.toolbar}>
        <div className={styles.viewModeButtons}>
          <button
            className={classNames(styles.modeButton, {
              [styles.active]: viewMode === 'edit',
            })}
            onClick={() => setViewMode('edit')}
            title="Edit mode"
          >
            <Edit size={14} />
            <span>Edit</span>
          </button>
          <button
            className={classNames(styles.modeButton, {
              [styles.active]: viewMode === 'split',
            })}
            onClick={() => setViewMode('split')}
            title="Split view"
          >
            <Columns size={14} />
            <span>Split</span>
          </button>
          <button
            className={classNames(styles.modeButton, {
              [styles.active]: viewMode === 'preview',
            })}
            onClick={() => setViewMode('preview')}
            title="Preview mode"
          >
            <Eye size={14} />
            <span>Preview</span>
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
              onChange={(e) => onChange(e.target.value)}
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