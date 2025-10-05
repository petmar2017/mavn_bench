import { useState, useEffect } from 'react';
import { Loader, FileBarChart, FileType, Network } from 'lucide-react';
import type { DocumentMessage } from '../../services/api';
import type { Entity } from '../../types/document';
import { documentContentService } from '../../services/documentContent';
import { ViewerTabBar } from './ViewerTabBar';
import type { ViewerTab } from './ViewerTabBar';
import { ViewerToolbar } from './ViewerToolbar';
import { SimpleMarkdownEditor } from './SimpleMarkdownEditor';
import { EntitiesViewer } from './EntitiesViewer';
import styles from './MarkdownEditor.module.css';

interface MarkdownEditorProps {
  document: DocumentMessage;
  onContentChange?: () => void;
  viewMode?: 'edit' | 'preview' | 'split';
  onDelete?: () => void;
  onDownload?: () => void;
  onHistory?: () => void;
}

type TabMode = 'summary' | 'content' | 'entities';

export const MarkdownEditor: React.FC<MarkdownEditorProps> = ({
  document,
  onContentChange,
  viewMode: initialViewMode,
  onDelete,
  onDownload,
  onHistory,
}) => {
  const [content, setContent] = useState('');
  const [summary, setSummary] = useState('');
  const [entities, setEntities] = useState<Entity[]>([]);
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
        const entitiesData = document.metadata.entities || [];
        setContent(text);
        setSummary(summaryText);
        setEntities(entitiesData);
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
    { id: 'entities', label: 'Entities', icon: <Network size={16} /> },
  ];

  return (
    <div className={styles.markdownEditor}>
      <ViewerTabBar
        tabs={tabs}
        activeTab={tabMode}
        onTabChange={(tabId) => setTabMode(tabId as TabMode)}
      />
      <ViewerToolbar
        documentId={document.metadata.document_id}
        isDeleted={document.metadata.deleted}
        onDelete={onDelete}
        onDownload={onDownload}
        onHistory={onHistory}
      />

      {tabMode === 'summary' ? (
        <SimpleMarkdownEditor
          documentId={document.metadata.document_id}
          content={summary}
          contentType="summary"
          label="Document Summary"
          onSave={(newSummary) => {
            setSummary(newSummary);
            documentContentService.clearCache(document.metadata.document_id);
          }}
        />
      ) : tabMode === 'content' ? (
        <SimpleMarkdownEditor
          documentId={document.metadata.document_id}
          content={content}
          contentType="content"
          label="Document Content"
          onSave={(newContent) => {
            setContent(newContent);
            setIsModified(false);
            documentContentService.clearCache(document.metadata.document_id);
          }}
        />
      ) : (
        <EntitiesViewer
          documentId={document.metadata.document_id}
          entities={entities}
          onEntitiesUpdate={(updatedEntities) => {
            setEntities(updatedEntities);
            documentContentService.clearCache(document.metadata.document_id);
          }}
        />
      )}
    </div>
  );
};