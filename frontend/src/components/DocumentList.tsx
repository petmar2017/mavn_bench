import React, { useEffect, useState } from 'react';
import {
  Box,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  TableContainer,
  IconButton,
  Badge,
  Text,
  HStack,
  VStack,
  Skeleton,
  Alert,
  AlertIcon,
  AlertDescription,
  useColorModeValue,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  useToast,
} from '@chakra-ui/react';
import { FileText, MoreVertical, Download, Trash2, Eye } from 'lucide-react';
import { documentApi, DocumentMessage } from '../services/api';
import { wsService } from '../services/websocket';

interface DocumentListProps {
  onDocumentSelect?: (document: DocumentMessage) => void;
  refresh?: number;
}

export const DocumentList: React.FC<DocumentListProps> = ({ onDocumentSelect, refresh }) => {
  const [documents, setDocuments] = useState<DocumentMessage[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  const fetchDocuments = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const docs = await documentApi.listDocuments();
      setDocuments(docs);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch documents');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [refresh]);

  useEffect(() => {
    // Subscribe to WebSocket events for real-time updates
    const unsubscribe = wsService.onSystemNotification((notification) => {
      if (notification.type === 'document_created' || notification.type === 'document_updated') {
        fetchDocuments();
      }
    });

    return () => {
      unsubscribe();
    };
  }, []);

  const handleDelete = async (documentId: string) => {
    try {
      await documentApi.deleteDocument(documentId);
      toast({
        title: 'Document deleted',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      fetchDocuments();
    } catch (err: any) {
      toast({
        title: 'Delete failed',
        description: err.response?.data?.detail || 'Failed to delete document',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  const getStatusBadge = (status?: string) => {
    const statusColors: Record<string, string> = {
      processing: 'blue',
      completed: 'green',
      failed: 'red',
      pending: 'gray',
    };
    const color = statusColors[status || 'pending'] || 'gray';
    return (
      <Badge colorScheme={color} variant="subtle">
        {status || 'pending'}
      </Badge>
    );
  };

  const getDocumentIcon = (type: string) => {
    return <FileText size={16} />;
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (isLoading) {
    return (
      <VStack spacing={3} align="stretch">
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} height="60px" />
        ))}
      </VStack>
    );
  }

  if (error) {
    return (
      <Alert status="error" borderRadius="lg">
        <AlertIcon />
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  if (documents.length === 0) {
    return (
      <Box
        p={8}
        textAlign="center"
        border="1px"
        borderColor={borderColor}
        borderRadius="lg"
      >
        <VStack spacing={3}>
          <FileText size={48} color="gray" />
          <Text fontSize="lg" fontWeight="medium">No documents yet</Text>
          <Text color="gray.500">Upload your first document to get started</Text>
        </VStack>
      </Box>
    );
  }

  return (
    <TableContainer>
      <Table variant="simple">
        <Thead>
          <Tr>
            <Th>Name</Th>
            <Th>Type</Th>
            <Th>Size</Th>
            <Th>Status</Th>
            <Th>Modified</Th>
            <Th width="50px"></Th>
          </Tr>
        </Thead>
        <Tbody>
          {documents.map((doc) => (
            <Tr
              key={doc.metadata.document_id}
              _hover={{ bg: useColorModeValue('gray.50', 'gray.700') }}
              cursor="pointer"
              onClick={() => onDocumentSelect?.(doc)}
            >
              <Td>
                <HStack spacing={2}>
                  {getDocumentIcon(doc.metadata.document_type)}
                  <Text fontWeight="medium">{doc.metadata.name}</Text>
                </HStack>
              </Td>
              <Td>
                <Badge variant="outline">{doc.metadata.document_type}</Badge>
              </Td>
              <Td>{formatFileSize(doc.metadata.size)}</Td>
              <Td>{getStatusBadge(doc.metadata.processing_status)}</Td>
              <Td>{formatDate(doc.metadata.updated_at)}</Td>
              <Td>
                <Menu>
                  <MenuButton
                    as={IconButton}
                    icon={<MoreVertical size={16} />}
                    variant="ghost"
                    size="sm"
                    onClick={(e) => e.stopPropagation()}
                  />
                  <MenuList>
                    <MenuItem icon={<Eye size={16} />} onClick={(e) => {
                      e.stopPropagation();
                      onDocumentSelect?.(doc);
                    }}>
                      View
                    </MenuItem>
                    <MenuItem icon={<Download size={16} />} onClick={(e) => {
                      e.stopPropagation();
                      // TODO: Implement download
                    }}>
                      Download
                    </MenuItem>
                    <MenuItem
                      icon={<Trash2 size={16} />}
                      color="red.500"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(doc.metadata.document_id);
                      }}
                    >
                      Delete
                    </MenuItem>
                  </MenuList>
                </Menu>
              </Td>
            </Tr>
          ))}
        </Tbody>
      </Table>
    </TableContainer>
  );
};