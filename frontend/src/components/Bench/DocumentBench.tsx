import { useRef, forwardRef, useImperativeHandle } from 'react';
import { MarkdownEditor } from './MarkdownEditor';
import { TextEditor, type TextEditorRef } from './TextEditor';
import { ExcelViewer } from './ExcelViewer';
import { JSONViewer } from './JSONViewer';
import { PDFViewer, type PDFViewerRef } from './PDFViewer';
import { WordViewer, type WordViewerRef } from './WordViewer';
import type { DocumentMessage } from '../../services/api';
import styles from './Bench.module.css';

interface DocumentBenchProps {
  document: DocumentMessage;
  onDocumentChange?: () => void;
}

export interface DocumentBenchRef {
  save: () => Promise<void>;
  hasUnsavedChanges: () => boolean;
}

export const DocumentBench = forwardRef<DocumentBenchRef, DocumentBenchProps>((
  { document, onDocumentChange },
  ref
) => {
  const textEditorRef = useRef<TextEditorRef>(null);
  const pdfViewerRef = useRef<PDFViewerRef>(null);
  const wordViewerRef = useRef<WordViewerRef>(null);
  const documentType = document.metadata.document_type.toLowerCase();

  // Expose save function to parent component
  useImperativeHandle(ref, () => ({
    save: async () => {
      if (documentType === 'text' && textEditorRef.current) {
        await textEditorRef.current.save();
      } else if (documentType === 'pdf' && pdfViewerRef.current) {
        await pdfViewerRef.current.save();
      } else if (documentType === 'word' && wordViewerRef.current) {
        await wordViewerRef.current.save();
      }
      // Add other document type save handlers here
    },
    hasUnsavedChanges: () => {
      if (documentType === 'text' && textEditorRef.current) {
        return textEditorRef.current.hasUnsavedChanges();
      } else if (documentType === 'pdf' && pdfViewerRef.current) {
        return pdfViewerRef.current.hasUnsavedChanges();
      } else if (documentType === 'word' && wordViewerRef.current) {
        return wordViewerRef.current.hasUnsavedChanges();
      }
      // Add other document type checks here
      return false;
    }
  }), [documentType]);

  // Route to appropriate viewer based on document type
  switch (documentType) {
    case 'text':
      return (
        <TextEditor
          ref={textEditorRef}
          document={document}
          onContentChange={onDocumentChange}
        />
      );

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
      return (
        <PDFViewer
          ref={pdfViewerRef}
          document={document}
          onContentChange={onDocumentChange}
        />
      );

    case 'word':
      return (
        <WordViewer
          ref={wordViewerRef}
          document={document}
          onContentChange={onDocumentChange}
        />
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
});

DocumentBench.displayName = 'DocumentBench';