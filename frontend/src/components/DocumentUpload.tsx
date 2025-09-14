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
    const timestamp = new Date().toISOString();
    logger.info(`[UPLOAD ${timestamp}] onDrop called`, {
      acceptedFiles: acceptedFiles.length,
      hasOnFileSelect: !!onFileSelect,
      uploadQueueLength: uploadQueue?.length || 0,
      hasActiveUploads
    });

    if (acceptedFiles.length === 0) {
      logger.warn(`[UPLOAD ${timestamp}] No files accepted - check file types`);
      return;
    }

    // First, add all files to the queue immediately (in pending state)
    const uploadIds: Array<{ file: File; uploadId: string | null }> = [];

    for (const file of acceptedFiles) {
      logger.info(`[UPLOAD ${timestamp}] Adding file to upload queue`, {
        fileName: file.name,
        fileSize: file.size,
        fileType: file.type || 'unknown',
        lastModified: file.lastModified
      });

      // Add to queue and get the upload ID - files start in 'pending' state by default
      const uploadId = onFileSelect ? onFileSelect(file) : null;
      uploadIds.push({ file, uploadId });

      logger.debug(`[UPLOAD ${timestamp}] File queue entry created`, {
        fileName: file.name,
        uploadId,
        hasOnFileSelect: !!onFileSelect
      });
    }

    logger.info(`[UPLOAD ${timestamp}] All files added to queue, starting processing`, {
      totalFiles: uploadIds.length,
      queueSnapshot: uploadIds.map(({ file, uploadId }) => ({
        name: file.name,
        uploadId
      }))
    });

    // Process files asynchronously after they're all in the queue
    // Use setTimeout to ensure UI updates first
    setTimeout(() => {
      logger.debug(`[UPLOAD ${timestamp}] Starting sequential upload processing`);
      processUploadsSequentially(uploadIds);
    }, 100);
  }, [onFileSelect, uploadQueue, hasActiveUploads]);

  // Separate function to process uploads sequentially
  const processUploadsSequentially = useCallback(async (uploadIds: Array<{ file: File; uploadId: string | null }>) => {
    const processTimestamp = new Date().toISOString();
    logger.info(`[UPLOAD-PROCESS ${processTimestamp}] Starting sequential processing`, {
      totalFiles: uploadIds.length,
      files: uploadIds.map(({ file, uploadId }) => ({ name: file.name, uploadId }))
    });

    for (const { file, uploadId } of uploadIds) {
      const fileTimestamp = new Date().toISOString();
      logger.info(`[UPLOAD-FILE ${fileTimestamp}] Processing file: ${file.name}`, {
        fileName: file.name,
        fileSize: file.size,
        uploadId,
        hasUpdateUploadItem: !!updateUploadItem
      });

      // Wait a moment before starting each upload to show pending state
      await new Promise(resolve => setTimeout(resolve, 500));

      // Update status to uploading
      if (uploadId && updateUploadItem) {
        logger.debug(`[UPLOAD-FILE ${fileTimestamp}] Updating status to uploading`, {
          fileName: file.name,
          uploadId
        });
        updateUploadItem(uploadId, { status: 'uploading', progress: 0 });
      } else {
        logger.warn(`[UPLOAD-FILE ${fileTimestamp}] Cannot update upload item - missing uploadId or updateUploadItem`, {
          fileName: file.name,
          hasUploadId: !!uploadId,
          hasUpdateUploadItem: !!updateUploadItem
        });
      }

      const formData = new FormData();
      formData.append('file', file);
      formData.append('name', file.name);
      formData.append('type', file.type || 'application/octet-stream');

      logger.debug(`[UPLOAD-FILE ${fileTimestamp}] FormData prepared`, {
        fileName: file.name,
        formDataEntries: Array.from(formData.entries()).map(([key, value]) => ({
          key,
          valueType: typeof value,
          valueSize: value instanceof File ? value.size : (value as string).length
        }))
      });

      // Don't set global uploading state for individual files
      // The queue will show individual file status
      try {
        // Simulate progress updates with delays
        if (uploadId && updateUploadItem) {
          setTimeout(() => {
            logger.debug(`[UPLOAD-FILE ${fileTimestamp}] Progress update: 20%`, { fileName: file.name });
            updateUploadItem(uploadId, { progress: 20 });
          }, 200);
          setTimeout(() => {
            logger.debug(`[UPLOAD-FILE ${fileTimestamp}] Progress update: 40%`, { fileName: file.name });
            updateUploadItem(uploadId, { progress: 40 });
          }, 400);
          setTimeout(() => {
            logger.debug(`[UPLOAD-FILE ${fileTimestamp}] Progress update: 60%`, { fileName: file.name });
            updateUploadItem(uploadId, { progress: 60 });
          }, 600);
        }

        logger.info(`[UPLOAD-API ${fileTimestamp}] Making API call to createDocument`, {
          fileName: file.name,
          fileSize: file.size,
          contentType: file.type
        });

        const response = await documentApi.createDocument(formData);

        logger.info(`[UPLOAD-API ${fileTimestamp}] API response received`, {
          fileName: file.name,
          hasResponse: !!response,
          responseId: response?.id,
          responseJobId: response?.job_id,
          responseType: typeof response,
          responseKeys: response ? Object.keys(response) : []
        });

        // Check if response is valid
        if (!response || !response.id) {
          const error = new Error('Invalid response from server');
          logger.error(`[UPLOAD-API ${fileTimestamp}] Invalid server response`, {
            fileName: file.name,
            response,
            hasResponse: !!response,
            responseId: response?.id
          });
          throw error;
        }

        // Check if we have a job_id (async processing)
        if (response.job_id) {
          // Async processing - update with job info
          const updateData = {
            status: 'processing',
            progress: 0,
            documentId: response.id,
            jobId: response.job_id,
            queuePosition: response.queue_position
          };

          logger.info(`[UPLOAD-ASYNC ${fileTimestamp}] File queued for async processing`, {
            fileName: file.name,
            documentId: response.id,
            jobId: response.job_id,
            queuePosition: response.queue_position,
            uploadId
          });

          if (uploadId && updateUploadItem) {
            updateUploadItem(uploadId, updateData);
            logger.debug(`[UPLOAD-ASYNC ${fileTimestamp}] Upload item updated with async processing info`, {
              fileName: file.name,
              updateData
            });
          }
        } else {
          // Sync processing (fallback) - mark as completed
          const updateData = {
            status: 'completed',
            progress: 100,
            documentId: response.id
          };

          logger.info(`[UPLOAD-SYNC ${fileTimestamp}] File uploaded successfully (sync processing)`, {
            fileName: file.name,
            documentId: response.id,
            uploadId
          });

          if (uploadId && updateUploadItem) {
            updateUploadItem(uploadId, updateData);
            logger.debug(`[UPLOAD-SYNC ${fileTimestamp}] Upload item updated with completion`, {
              fileName: file.name,
              updateData
            });
          }
        }

        // Only show success state if this was the last file in a batch
        const remainingUploads = uploadQueue?.filter(item =>
          item.status === 'pending' || item.status === 'uploading' || item.status === 'processing'
        ).length || 0;

        logger.debug(`[UPLOAD-STATUS ${fileTimestamp}] Checking batch completion`, {
          fileName: file.name,
          remainingUploads,
          uploadQueueLength: uploadQueue?.length || 0
        });

        if (remainingUploads <= 1) { // This file plus any remaining
          logger.info(`[UPLOAD-STATUS ${fileTimestamp}] Batch upload completed - showing success state`, {
            fileName: file.name,
            remainingUploads
          });
          setUploadState({ isUploading: false, error: null, success: true });
          // Reset success state after 3 seconds
          setTimeout(() => {
            logger.debug(`[UPLOAD-STATUS ${fileTimestamp}] Resetting success state`);
            setUploadState(prev => ({ ...prev, success: false }));
          }, 3000);
        }

        // Call the success callback with upload ID
        if (onUploadSuccess) {
          logger.debug(`[UPLOAD-CALLBACK ${fileTimestamp}] Calling onUploadSuccess callback`, {
            fileName: file.name,
            documentId: response.id,
            uploadId
          });
          onUploadSuccess(response, uploadId || undefined);
        } else {
          logger.debug(`[UPLOAD-CALLBACK ${fileTimestamp}] No onUploadSuccess callback provided`);
        }
      } catch (error: any) {
        const errorMessage = error.response?.data?.detail || 'Upload failed. Please try again.';

        // Log the error with full context
        logApiError('/api/documents', error);
        logger.error(`[UPLOAD-ERROR ${fileTimestamp}] File upload failed`, {
          fileName: file.name,
          errorMessage,
          statusCode: error.response?.status,
          errorType: error.name,
          errorStack: error.stack,
          uploadId,
          hasResponse: !!error.response,
          responseData: error.response?.data
        });

        // Update queue item with error
        if (uploadId && updateUploadItem) {
          const errorData = {
            status: 'error',
            error: errorMessage
          };
          updateUploadItem(uploadId, errorData);
          logger.debug(`[UPLOAD-ERROR ${fileTimestamp}] Upload item updated with error`, {
            fileName: file.name,
            errorData
          });
        }

        // Only set error state if there are no more files being processed
        const otherActiveUploads = uploadQueue?.filter(item =>
          item.id !== uploadId && (item.status === 'uploading' || item.status === 'processing')
        ).length || 0;

        logger.debug(`[UPLOAD-ERROR ${fileTimestamp}] Checking if should show global error state`, {
          fileName: file.name,
          otherActiveUploads,
          uploadId
        });

        if (otherActiveUploads === 0) {
          logger.info(`[UPLOAD-ERROR ${fileTimestamp}] Setting global error state - no other active uploads`, {
            fileName: file.name,
            errorMessage
          });
          setUploadState({
            isUploading: false,
            error: errorMessage,
            success: false,
          });
        }
      }
    }

    logger.info(`[UPLOAD-PROCESS ${processTimestamp}] Sequential processing completed`, {
      totalFiles: uploadIds.length,
      processedFiles: uploadIds.map(({ file }) => file.name)
    });
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