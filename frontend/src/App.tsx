import React, { useState, useEffect } from 'react';
import {
  ChakraProvider,
  Box,
  Container,
  VStack,
  Heading,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  useToast,
  IconButton,
  HStack,
  Text,
  useColorMode,
  useColorModeValue,
  Divider,
} from '@chakra-ui/react';
import { Moon, Sun, FileText } from 'lucide-react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DocumentUpload } from './components/DocumentUpload';
import { DocumentList } from './components/DocumentList';
import { SearchInterface } from './components/SearchInterface';
import { wsService } from './services/websocket';
import { DocumentMessage } from './services/api';

const queryClient = new QueryClient();

function AppContent() {
  const [refreshDocuments, setRefreshDocuments] = useState(0);
  const [selectedDocument, setSelectedDocument] = useState<DocumentMessage | null>(null);
  const { colorMode, toggleColorMode } = useColorMode();
  const toast = useToast();

  const bgColor = useColorModeValue('gray.50', 'gray.900');
  const cardBg = useColorModeValue('white', 'gray.800');

  useEffect(() => {
    // Connect to WebSocket
    wsService.connect();

    // Subscribe to system notifications
    const unsubscribe = wsService.onSystemNotification((notification) => {
      toast({
        title: notification.title || 'System Notification',
        description: notification.message,
        status: notification.type || 'info',
        duration: 5000,
        isClosable: true,
      });
    });

    return () => {
      unsubscribe();
      wsService.disconnect();
    };
  }, [toast]);

  const handleUploadSuccess = (document: DocumentMessage) => {
    toast({
      title: 'Upload successful',
      description: `${document.metadata.name} has been uploaded`,
      status: 'success',
      duration: 5000,
      isClosable: true,
    });
    setRefreshDocuments(prev => prev + 1);
  };

  const handleDocumentSelect = (document: DocumentMessage) => {
    setSelectedDocument(document);
    // You can add logic here to show document details in a modal or side panel
  };

  const handleSearchResultSelect = (result: any) => {
    // Handle search result selection
    console.log('Selected search result:', result);
  };

  return (
    <Box minH="100vh" bg={bgColor}>
      <Container maxW="container.xl" py={8}>
        <VStack spacing={8} align="stretch">
          {/* Header */}
          <HStack justify="space-between" align="center">
            <HStack spacing={3}>
              <FileText size={32} />
              <Heading size="lg">Mavn Bench</Heading>
            </HStack>
            <HStack spacing={4}>
              <Text fontSize="sm" color="gray.500">
                Document Processing Platform
              </Text>
              <IconButton
                aria-label="Toggle color mode"
                icon={colorMode === 'light' ? <Moon size={20} /> : <Sun size={20} />}
                onClick={toggleColorMode}
                variant="ghost"
              />
            </HStack>
          </HStack>

          <Divider />

          {/* Main Content */}
          <Tabs variant="enclosed" colorScheme="blue">
            <TabList>
              <Tab>Upload</Tab>
              <Tab>Documents</Tab>
              <Tab>Search</Tab>
            </TabList>

            <TabPanels>
              {/* Upload Tab */}
              <TabPanel>
                <VStack spacing={6} align="stretch">
                  <Box>
                    <Heading size="md" mb={2}>Upload Document</Heading>
                    <Text color="gray.500" fontSize="sm">
                      Drag and drop or click to upload PDF, Word, Text, Markdown, CSV, or JSON files
                    </Text>
                  </Box>
                  <Box bg={cardBg} p={6} borderRadius="lg" shadow="sm">
                    <DocumentUpload onUploadSuccess={handleUploadSuccess} />
                  </Box>
                </VStack>
              </TabPanel>

              {/* Documents Tab */}
              <TabPanel>
                <VStack spacing={6} align="stretch">
                  <Box>
                    <Heading size="md" mb={2}>Document Library</Heading>
                    <Text color="gray.500" fontSize="sm">
                      View and manage your uploaded documents
                    </Text>
                  </Box>
                  <Box bg={cardBg} p={6} borderRadius="lg" shadow="sm">
                    <DocumentList
                      refresh={refreshDocuments}
                      onDocumentSelect={handleDocumentSelect}
                    />
                  </Box>
                </VStack>
              </TabPanel>

              {/* Search Tab */}
              <TabPanel>
                <VStack spacing={6} align="stretch">
                  <Box>
                    <Heading size="md" mb={2}>Search Documents</Heading>
                    <Text color="gray.500" fontSize="sm">
                      Search across your documents using vector, full-text, graph, or hybrid search
                    </Text>
                  </Box>
                  <Box bg={cardBg} p={6} borderRadius="lg" shadow="sm">
                    <SearchInterface onResultSelect={handleSearchResultSelect} />
                  </Box>
                </VStack>
              </TabPanel>
            </TabPanels>
          </Tabs>
        </VStack>
      </Container>
    </Box>
  );
}

function App() {
  return (
    <ChakraProvider>
      <QueryClientProvider client={queryClient}>
        <AppContent />
      </QueryClientProvider>
    </ChakraProvider>
  );
}

export default App;