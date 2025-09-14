import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, CheckCircle, AlertCircle } from 'lucide-react';
import classNames from 'classnames';
import { documentApi } from '../services/api';
import { logger, logApiError } from '../services/logging';
import styles from './DocumentUpload.module.css';

interface UploadState {
  isUploading: boolean;
  error: string | null;
  success: boolean;
}

interface DocumentUploadProps {
  onUploadSuccess?: (document: any) => void;
}

export const DocumentUpload: React.FC<DocumentUploadProps> = ({ onUploadSuccess }) => {
  const [uploadState, setUploadState] = useState<UploadState>({
    isUploading: false,
    error: null,
    success: false,
  });

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    const file = acceptedFiles[0];
    logger.info('Starting file upload', {
      fileName: file.name,
      fileSize: file.size,
      fileType: file.type || 'unknown'
    });

    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', file.name);
    formData.append('type', file.type || 'application/octet-stream');

    setUploadState({ isUploading: true, error: null, success: false });

    try {
      const response = await documentApi.createDocument(formData);

      // Check if response is valid
      if (!response || !response.id) {
        throw new Error('Invalid response from server');
      }

      logger.info('File uploaded successfully', {
        fileName: file.name,
        documentId: response.id
      });

      setUploadState({ isUploading: false, error: null, success: true });
      onUploadSuccess?.(response);

      // Reset success state after 3 seconds
      setTimeout(() => {
        setUploadState(prev => ({ ...prev, success: false }));
      }, 3000);
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Upload failed. Please try again.';

      // Log the error with full context
      logApiError('/api/documents', error);
      logger.error('File upload failed', {
        fileName: file.name,
        errorMessage,
        statusCode: error.response?.status
      });

      setUploadState({
        isUploading: false,
        error: errorMessage,
        success: false,
      });
    }
  }, [onUploadSuccess]);

  const { getRootProps, getInputProps, isDragActive, acceptedFiles } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
      'text/csv': ['.csv'],
      'application/json': ['.json'],
    },
    maxFiles: 1,
    disabled: uploadState.isUploading,
  });

  return (
    <div className={styles.container}>
      <div
        {...getRootProps()}
        className={classNames(styles.dropzone, {
          [styles.uploading]: uploadState.isUploading,
          [styles.success]: uploadState.success,
          [styles.error]: uploadState.error,
        })}
      >
        <input {...getInputProps()} />

        {uploadState.isUploading ? (
          <div className={styles.dropzoneContent}>
            <div className={styles.spinner} />
            <div className={styles.uploadingText}>Uploading...</div>
          </div>
        ) : uploadState.success ? (
          <div className={styles.dropzoneContent}>
            <CheckCircle size={48} className={styles.successIcon} />
            <div className={styles.successText}>
              Upload successful!
            </div>
            <div className={styles.subtitle}>
              Switching to Documents tab...
            </div>
          </div>
        ) : (
          <div className={styles.dropzoneContent}>
            <Upload size={48} className={styles.icon} />
            <div className={styles.title}>
              {isDragActive ? 'Drop the file here' : 'Drag & drop a file here'}
            </div>
            <div className={styles.subtitle}>
              or click to select
            </div>
            <div className={styles.badges}>
              <span className={styles.badge}>PDF</span>
              <span className={styles.badge}>Word</span>
              <span className={styles.badge}>Text</span>
              <span className={styles.badge}>Markdown</span>
              <span className={styles.badge}>CSV</span>
              <span className={styles.badge}>JSON</span>
            </div>
          </div>
        )}
      </div>

      {uploadState.error && (
        <div className={styles.alert}>
          <AlertCircle size={20} className={styles.alertIcon} />
          <span className={styles.alertText}>{uploadState.error}</span>
        </div>
      )}

      {acceptedFiles.length > 0 && !uploadState.isUploading && !uploadState.error && (
        <div className={styles.fileInfo}>
          <div className={styles.fileInfoText}>
            Selected: {acceptedFiles[0].name} ({(acceptedFiles[0].size / 1024).toFixed(2)} KB)
          </div>
        </div>
      )}
    </div>
  );
};