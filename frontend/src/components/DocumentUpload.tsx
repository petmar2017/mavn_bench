import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  Box,
  VStack,
  Text,
  Icon,
  Alert,
  AlertIcon,
  AlertDescription,
  Spinner,
  HStack,
  Tag,
  useColorModeValue,
} from '@chakra-ui/react';
import { Upload, CheckCircle } from 'lucide-react';
import { documentApi } from '../services/api';

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

  const borderColor = useColorModeValue('gray.300', 'gray.600');
  const hoverBorderColor = useColorModeValue('gray.400', 'gray.500');
  const activeBgColor = useColorModeValue('blue.50', 'blue.900');

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    const file = acceptedFiles[0];
    const formData = new FormData();
    formData.append('file', file);

    setUploadState({ isUploading: true, error: null, success: false });

    try {
      const document = await documentApi.createDocument(formData);
      setUploadState({ isUploading: false, error: null, success: true });
      onUploadSuccess?.(document);

      // Reset success state after 3 seconds
      setTimeout(() => {
        setUploadState(prev => ({ ...prev, success: false }));
      }, 3000);
    } catch (error: any) {
      setUploadState({
        isUploading: false,
        error: error.response?.data?.detail || 'Upload failed',
        success: false,
      });
    }
  }, [onUploadSuccess]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
      'text/csv': ['.csv'],
      'application/json': ['.json'],
      'application/xml': ['.xml'],
    },
    maxFiles: 1,
    disabled: uploadState.isUploading,
  });

  return (
    <Box w="full">
      <Box
        {...getRootProps()}
        border="2px"
        borderStyle="dashed"
        borderColor={isDragActive ? 'blue.500' : borderColor}
        borderRadius="lg"
        p={8}
        textAlign="center"
        cursor={uploadState.isUploading ? 'not-allowed' : 'pointer'}
        transition="all 0.2s"
        bg={isDragActive ? activeBgColor : 'transparent'}
        _hover={{
          borderColor: uploadState.isUploading ? borderColor : hoverBorderColor,
        }}
        opacity={uploadState.isUploading ? 0.5 : 1}
      >
        <input {...getInputProps()} />

        <VStack spacing={4}>
          {uploadState.isUploading ? (
            <>
              <Spinner size="xl" color="blue.500" thickness="3px" />
              <Text color="gray.600">Uploading...</Text>
            </>
          ) : uploadState.success ? (
            <>
              <Icon as={CheckCircle} boxSize={12} color="green.500" />
              <Text color="green.600" fontWeight="medium">Upload successful!</Text>
            </>
          ) : (
            <>
              <Icon as={Upload} boxSize={12} color="gray.400" />
              <VStack spacing={1}>
                <Text fontSize="lg" fontWeight="medium">
                  {isDragActive ? 'Drop the file here' : 'Drag & drop a file here'}
                </Text>
                <Text fontSize="sm" color="gray.500">
                  or click to select
                </Text>
              </VStack>
              <HStack spacing={2} flexWrap="wrap" justify="center">
                <Tag size="sm" variant="subtle">PDF</Tag>
                <Tag size="sm" variant="subtle">Word</Tag>
                <Tag size="sm" variant="subtle">Text</Tag>
                <Tag size="sm" variant="subtle">Markdown</Tag>
                <Tag size="sm" variant="subtle">CSV</Tag>
                <Tag size="sm" variant="subtle">JSON</Tag>
              </HStack>
            </>
          )}
        </VStack>
      </Box>

      {uploadState.error && (
        <Alert status="error" mt={4} borderRadius="lg">
          <AlertIcon />
          <AlertDescription>{uploadState.error}</AlertDescription>
        </Alert>
      )}
    </Box>
  );
};