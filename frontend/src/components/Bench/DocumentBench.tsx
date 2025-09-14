import { MarkdownEditor } from './MarkdownEditor';
import { ExcelViewer } from './ExcelViewer';
import { JSONViewer } from './JSONViewer';
import { PDFViewer } from './PDFViewer';
import type { DocumentMessage } from '../../services/api';
import styles from './Bench.module.css';

interface DocumentBenchProps {
  document: DocumentMessage;
  onDocumentChange?: () => void;
}

export const DocumentBench: React.FC<DocumentBenchProps> = ({
  document,
  onDocumentChange,
}) => {
  const documentType = document.metadata.document_type.toLowerCase();

  // Route to appropriate viewer based on document type
  switch (documentType) {
    case 'markdown':
    case 'webpage':
    case 'youtube':
    case 'podcast':
      return (
        <MarkdownEditor
          document={document}
          onContentChange={onDocumentChange}
        />
      );

    case 'csv':
    case 'excel':
      return (
        <ExcelViewer
          document={document}
          onCellChange={onDocumentChange}
        />
      );

    case 'json':
    case 'xml':
      return (
        <JSONViewer
          document={document}
        />
      );

    case 'pdf':
      return <PDFViewer document={document} />;

    case 'word':
      return (
        <div className={styles.viewerContainer}>
          <div className={styles.wordViewer}>
            <h3>Word Document</h3>
            <pre>{document.content?.text || 'No content available'}</pre>
          </div>
        </div>
      );

    default:
      return (
        <div className={styles.viewerContainer}>
          <div className={styles.defaultViewer}>
            <h3>Document Preview</h3>
            <p>Document type: {documentType}</p>
            <pre>{document.content?.text || JSON.stringify(document.content, null, 2)}</pre>
          </div>
        </div>
      );
  }
};