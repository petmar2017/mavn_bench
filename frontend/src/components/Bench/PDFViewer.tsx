import { useState, useEffect } from 'react';
import { FileText, Loader } from 'lucide-react';
import type { DocumentMessage } from '../../services/api';
import { documentContentService } from '../../services/documentContent';
import { MarkdownEditor } from './MarkdownEditor';
import styles from './Bench.module.css';

interface PDFViewerProps {
  document: DocumentMessage;
}

export const PDFViewer: React.FC<PDFViewerProps> = ({ document }) => {
  const [content, setContent] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadContent = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const documentId = document.metadata.document_id;
        const contentData = await documentContentService.getContent(documentId);

        // For PDFs, the backend converts to markdown, so we should use formatted_content or text
        const pdfContent = contentData.formatted_content || contentData.text || contentData.raw_text || '';

        setContent(pdfContent);
      } catch (err) {
        console.error('Failed to load PDF content:', err);
        setError('Failed to load PDF content');
      } finally {
        setIsLoading(false);
      }
    };

    loadContent();
  }, [document.metadata.document_id]);

  if (isLoading) {
    return (
      <div className={styles.viewerContainer}>
        <div className={styles.loadingContainer}>
          <Loader size={32} className={styles.spinner} />
          <p>Loading PDF content...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.viewerContainer}>
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

  // If we have markdown content from PDF conversion, use the MarkdownEditor in preview mode
  if (content && content.includes('## Page')) {
    // Create a temporary document with the PDF content for the MarkdownEditor
    const tempDoc = {
      ...document,
      content: { ...document.content, text: content }
    };

    return <MarkdownEditor document={tempDoc} viewMode="preview" />;
  }

  // Fallback to basic display if content doesn't look like markdown
  return (
    <div className={styles.viewerContainer}>
      <div className={styles.pdfViewer}>
        <div className={styles.pdfHeader}>
          <FileText size={24} />
          <h3>PDF Document: {document.metadata.name}</h3>
        </div>
        {content ? (
          <div className={styles.pdfContent}>
            <pre>{content}</pre>
          </div>
        ) : (
          <div className={styles.emptyState}>
            <p>No content available for this PDF</p>
            <p className={styles.hint}>The PDF may not have been processed correctly</p>
          </div>
        )}
      </div>
    </div>
  );
};