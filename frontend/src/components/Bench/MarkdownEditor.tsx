import { useState, useEffect } from 'react';
import { Loader, FileBarChart, FileType } from 'lucide-react';
import type { DocumentMessage } from '../../services/api';
import { documentContentService } from '../../services/documentContent';
import { ViewerTabBar } from './ViewerTabBar';
import type { ViewerTab } from './ViewerTabBar';
import { SummaryEditor } from './SummaryEditor';
import { MarkdownContentEditor } from './MarkdownContentEditor';
import styles from './MarkdownEditor.module.css';

interface MarkdownEditorProps {
  document: DocumentMessage;
  onContentChange?: () => void;
  viewMode?: 'edit' | 'preview' | 'split';
}

type TabMode = 'summary' | 'content';

export const MarkdownEditor: React.FC<MarkdownEditorProps> = ({
  document,
  onContentChange,
  viewMode: initialViewMode,
}) => {
  const [content, setContent] = useState('');
  const [summary, setSummary] = useState('');
  const [tabMode, setTabMode] = useState<TabMode>('summary');
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
        const summaryText = contentData.summary || '';
        setContent(text);
        setSummary(summaryText);
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

  const tabs: ViewerTab[] = [
    { id: 'summary', label: 'Summary', icon: <FileBarChart size={16} /> },
    { id: 'content', label: 'Content', icon: <FileType size={16} /> },
  ];

  return (
    <div className={styles.markdownEditor}>
      <ViewerTabBar
        tabs={tabs}
        activeTab={tabMode}
        onTabChange={(tabId) => setTabMode(tabId as TabMode)}
      />

      {tabMode === 'summary' ? (
        <SummaryEditor
          documentId={document.metadata.document_id}
          summary={summary}
          onSave={(newSummary) => {
            setSummary(newSummary);
            documentContentService.clearCache(document.metadata.document_id);
          }}
        />
      ) : (
        <MarkdownContentEditor
          content={content}
          onChange={handleContentChange}
          isModified={isModified}
        />
      )}
    </div>
  );
};