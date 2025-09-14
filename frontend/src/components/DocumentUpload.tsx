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
  onUploadSuccess?: (document: any, uploadId?: string) => void;
  onFileSelect?: (file: File) => string;
  updateUploadItem?: (id: string, updates: any) => void;
  uploadQueue?: any[];
}

export const DocumentUpload: React.FC<DocumentUploadProps> = ({
  onUploadSuccess,
  onFileSelect,
  updateUploadItem,
  uploadQueue
}) => {
  const [uploadState, setUploadState] = useState<UploadState>({
    isUploading: false,
    error: null,
    success: false,
  });

  // Check if any items are currently uploading
  const hasActiveUploads = uploadQueue?.some(item =>
    item.status === 'uploading' || item.status === 'processing'
  ) || false;

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    // First, add all files to the queue immediately (in pending state)
    const uploadIds: Array<{ file: File; uploadId: string | null }> = [];

    for (const file of acceptedFiles) {
      logger.info('Adding file to upload queue', {
        fileName: file.name,
        fileSize: file.size,
        fileType: file.type || 'unknown'
      });

      // Add to queue and get the upload ID - files start in 'pending' state by default
      const uploadId = onFileSelect ? onFileSelect(file) : null;
      uploadIds.push({ file, uploadId });
    }

    // Process files asynchronously after they're all in the queue
    // Use setTimeout to ensure UI updates first
    setTimeout(() => {
      processUploadsSequentially(uploadIds);
    }, 100);
  }, [onFileSelect]);

  // Separate function to process uploads sequentially
  const processUploadsSequentially = useCallback(async (uploadIds: Array<{ file: File; uploadId: string | null }>) => {
    for (const { file, uploadId } of uploadIds) {
      // Wait a moment before starting each upload to show pending state
      await new Promise(resolve => setTimeout(resolve, 500));

      // Update status to uploading
      if (uploadId && updateUploadItem) {
        updateUploadItem(uploadId, { status: 'uploading', progress: 0 });
      }

      const formData = new FormData();
      formData.append('file', file);
      formData.append('name', file.name);
      formData.append('type', file.type || 'application/octet-stream');

      // Don't set global uploading state for individual files
      // The queue will show individual file status
      try {
        // Simulate progress updates with delays
        if (uploadId && updateUploadItem) {
          setTimeout(() => updateUploadItem(uploadId, { progress: 20 }), 200);
          setTimeout(() => updateUploadItem(uploadId, { progress: 40 }), 400);
          setTimeout(() => updateUploadItem(uploadId, { progress: 60 }), 600);
        }

        const response = await documentApi.createDocument(formData);

        // Check if response is valid
        if (!response || !response.id) {
          throw new Error('Invalid response from server');
        }

        // Update to processing status
        if (uploadId && updateUploadItem) {
          updateUploadItem(uploadId, { status: 'processing', progress: 80 });
        }

        logger.info('File uploaded successfully', {
          fileName: file.name,
          documentId: response.id
        });

        // Mark as completed
        if (uploadId && updateUploadItem) {
          setTimeout(() => {
            updateUploadItem(uploadId, { status: 'completed', progress: 100 });
          }, 500);
        }

        // Only show success state if this was the last file in a batch
        const remainingUploads = uploadQueue?.filter(item =>
          item.status === 'pending' || item.status === 'uploading' || item.status === 'processing'
        ).length || 0;

        if (remainingUploads <= 1) { // This file plus any remaining
          setUploadState({ isUploading: false, error: null, success: true });
          // Reset success state after 3 seconds
          setTimeout(() => {
            setUploadState(prev => ({ ...prev, success: false }));
          }, 3000);
        }

        // Call the success callback with upload ID
        onUploadSuccess?.(response, uploadId || undefined);
      } catch (error: any) {
        const errorMessage = error.response?.data?.detail || 'Upload failed. Please try again.';

        // Log the error with full context
        logApiError('/api/documents', error);
        logger.error('File upload failed', {
          fileName: file.name,
          errorMessage,
          statusCode: error.response?.status
        });

        // Update queue item with error
        if (uploadId && updateUploadItem) {
          updateUploadItem(uploadId, {
            status: 'error',
            error: errorMessage
          });
        }

        // Only set error state if there are no more files being processed
        const otherActiveUploads = uploadQueue?.filter(item =>
          item.id !== uploadId && (item.status === 'uploading' || item.status === 'processing')
        ).length || 0;

        if (otherActiveUploads === 0) {
          setUploadState({
            isUploading: false,
            error: errorMessage,
            success: false,
          });
        }
      }
    }
  }, [onUploadSuccess, updateUploadItem, uploadQueue]);

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
    multiple: true,  // Allow multiple file selection
    disabled: hasActiveUploads,
  });

  return (
    <div className={styles.container}>
      <div
        {...getRootProps()}
        className={classNames(styles.dropzone, {
          [styles.uploading]: hasActiveUploads,
          [styles.success]: uploadState.success,
          [styles.error]: uploadState.error,
        })}
      >
        <input {...getInputProps()} />

        {hasActiveUploads ? (
          <div className={styles.dropzoneContent}>
            <div className={styles.spinner} />
            <div className={styles.uploadingText}>Processing files...</div>
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