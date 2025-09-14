import { useState, useEffect } from 'react';
import { ChevronRight, ChevronDown, Copy, Download, Loader } from 'lucide-react';
import classNames from 'classnames';
import type { DocumentMessage } from '../../services/api';
import { documentContentService } from '../../services/documentContent';
import styles from './Bench.module.css';

interface JSONViewerProps {
  document: DocumentMessage;
}

interface TreeNodeProps {
  keyName: string;
  value: any;
  level?: number;
  isLast?: boolean;
}

const TreeNode: React.FC<TreeNodeProps> = ({ keyName, value, level = 0, isLast = false }) => {
  const [isExpanded, setIsExpanded] = useState(level < 2); // Auto-expand first 2 levels

  const isObject = value !== null && typeof value === 'object' && !Array.isArray(value);
  const isArray = Array.isArray(value);
  const isExpandable = isObject || isArray;

  const getValuePreview = () => {
    if (isObject) {
      const keys = Object.keys(value);
      return `{${keys.length} ${keys.length === 1 ? 'property' : 'properties'}}`;
    }
    if (isArray) {
      return `[${value.length} ${value.length === 1 ? 'item' : 'items'}]`;
    }
    if (typeof value === 'string') {
      return `"${value}"`;
    }
    if (value === null) {
      return 'null';
    }
    if (value === undefined) {
      return 'undefined';
    }
    return String(value);
  };

  const getValueClass = () => {
    if (typeof value === 'string') return styles.stringValue;
    if (typeof value === 'number') return styles.numberValue;
    if (typeof value === 'boolean') return styles.booleanValue;
    if (value === null || value === undefined) return styles.nullValue;
    return '';
  };

  return (
    <div className={styles.treeNode} style={{ marginLeft: `${level * 20}px` }}>
      <div className={styles.nodeHeader}>
        {isExpandable && (
          <button
            className={styles.expandButton}
            onClick={() => setIsExpanded(!isExpanded)}
          >
            {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </button>
        )}
        <span className={styles.nodeKey}>{keyName}:</span>
        {!isExpandable && (
          <span className={classNames(styles.nodeValue, getValueClass())}>
            {getValuePreview()}
          </span>
        )}
        {isExpandable && !isExpanded && (
          <span className={styles.collapsedPreview}>{getValuePreview()}</span>
        )}
      </div>

      {isExpandable && isExpanded && (
        <div className={styles.nodeChildren}>
          {isObject &&
            Object.entries(value).map(([key, val], index, arr) => (
              <TreeNode
                key={key}
                keyName={key}
                value={val}
                level={level + 1}
                isLast={index === arr.length - 1}
              />
            ))}
          {isArray &&
            value.map((item: any, index: number) => (
              <TreeNode
                key={index}
                keyName={`[${index}]`}
                value={item}
                level={level + 1}
                isLast={index === value.length - 1}
              />
            ))}
        </div>
      )}
    </div>
  );
};

export const JSONViewer: React.FC<JSONViewerProps> = ({ document }) => {
  const [jsonData, setJsonData] = useState<any>(null);
  const [rawView, setRawView] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadContent = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const documentId = document.metadata.document_id;
        const contentData = await documentContentService.getContent(documentId);

        let data;
        const text = contentData.text || contentData.formatted_content || contentData.raw_text;

        if (text) {
          if (typeof text === 'string') {
            data = JSON.parse(text);
          } else {
            data = text;
          }
        } else {
          data = {};
        }

        setJsonData(data);
        setError(null);
      } catch (e) {
        console.error('Failed to parse JSON content:', e);
        setError('Failed to parse JSON content');
        setJsonData(null);
      } finally {
        setIsLoading(false);
      }
    };

    loadContent();
  }, [document.metadata.document_id]);

  const copyToClipboard = () => {
    const text = JSON.stringify(jsonData, null, 2);
    navigator.clipboard.writeText(text);
  };

  const downloadJSON = () => {
    const text = JSON.stringify(jsonData, null, 2);
    const blob = new Blob([text], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${document.metadata.name}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  if (isLoading) {
    return (
      <div className={styles.jsonViewer}>
        <div className={styles.loadingContainer}>
          <Loader size={32} className={styles.spinner} />
          <p>Loading JSON data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.jsonViewer}>
        <div className={styles.errorMessage}>
          <h3>Error</h3>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.jsonViewer}>
      <div className={styles.jsonToolbar}>
        <div className={styles.viewToggle}>
          <button
            className={classNames(styles.toggleButton, { [styles.active]: !rawView })}
            onClick={() => setRawView(false)}
          >
            Tree View
          </button>
          <button
            className={classNames(styles.toggleButton, { [styles.active]: rawView })}
            onClick={() => setRawView(true)}
          >
            Raw JSON
          </button>
        </div>

        <div className={styles.jsonActions}>
          <button
            className={styles.actionButton}
            onClick={copyToClipboard}
            title="Copy to clipboard"
          >
            <Copy size={16} />
          </button>
          <button
            className={styles.actionButton}
            onClick={downloadJSON}
            title="Download JSON"
          >
            <Download size={16} />
          </button>
        </div>
      </div>

      <div className={styles.jsonContent}>
        {rawView ? (
          <pre className={styles.rawJson}>
            {JSON.stringify(jsonData, null, 2)}
          </pre>
        ) : (
          <div className={styles.treeView}>
            {jsonData &&
              (typeof jsonData === 'object' && !Array.isArray(jsonData) ? (
                Object.entries(jsonData).map(([key, value], index, arr) => (
                  <TreeNode
                    key={key}
                    keyName={key}
                    value={value}
                    level={0}
                    isLast={index === arr.length - 1}
                  />
                ))
              ) : (
                <TreeNode keyName="root" value={jsonData} level={0} />
              ))}
          </div>
        )}
      </div>
    </div>
  );
};