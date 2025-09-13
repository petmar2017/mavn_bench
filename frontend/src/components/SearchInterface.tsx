import React, { useState } from 'react';
import {
  Box,
  Input,
  InputGroup,
  InputLeftElement,
  InputRightElement,
  Button,
  VStack,
  HStack,
  Text,
  Badge,
  Card,
  CardBody,
  Select,
  Spinner,
  Alert,
  AlertIcon,
  AlertDescription,
  useColorModeValue,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Progress,
} from '@chakra-ui/react';
import { Search, X } from 'lucide-react';
import { searchApi, SearchResult } from '../services/api';

interface SearchInterfaceProps {
  onResultSelect?: (result: SearchResult) => void;
}

type SearchType = 'vector' | 'fulltext' | 'graph' | 'hybrid';

export const SearchInterface: React.FC<SearchInterfaceProps> = ({ onResultSelect }) => {
  const [query, setQuery] = useState('');
  const [searchType, setSearchType] = useState<SearchType>('vector');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');

  const handleSearch = async () => {
    if (!query.trim()) return;

    setIsSearching(true);
    setError(null);
    setResults([]);

    try {
      let searchResults: SearchResult[];
      const searchQuery = { query, limit: 20 };

      switch (searchType) {
        case 'vector':
          searchResults = await searchApi.vectorSearch(searchQuery);
          break;
        case 'fulltext':
          searchResults = await searchApi.fulltextSearch(searchQuery);
          break;
        case 'graph':
          searchResults = await searchApi.graphSearch(searchQuery);
          break;
        case 'hybrid':
          searchResults = await searchApi.hybridSearch(searchQuery);
          break;
        default:
          searchResults = await searchApi.vectorSearch(searchQuery);
      }

      setResults(searchResults);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Search failed. Please try again.');
    } finally {
      setIsSearching(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const clearSearch = () => {
    setQuery('');
    setResults([]);
    setError(null);
  };

  const getScoreColor = (score: number) => {
    if (score > 0.8) return 'green';
    if (score > 0.6) return 'yellow';
    return 'orange';
  };

  return (
    <VStack spacing={4} align="stretch">
      <Box>
        <InputGroup size="lg">
          <InputLeftElement pointerEvents="none">
            <Search size={20} color="gray" />
          </InputLeftElement>
          <Input
            placeholder="Search documents..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            pr="8rem"
          />
          <InputRightElement width="8rem">
            {query && (
              <Button
                size="sm"
                variant="ghost"
                onClick={clearSearch}
                mr={1}
              >
                <X size={16} />
              </Button>
            )}
            <Button
              size="sm"
              colorScheme="blue"
              onClick={handleSearch}
              isLoading={isSearching}
              loadingText="Search"
            >
              Search
            </Button>
          </InputRightElement>
        </InputGroup>
      </Box>

      <Tabs
        variant="soft-rounded"
        colorScheme="blue"
        onChange={(index) => {
          const types: SearchType[] = ['vector', 'fulltext', 'graph', 'hybrid'];
          setSearchType(types[index]);
        }}
      >
        <TabList>
          <Tab>Vector</Tab>
          <Tab>Full Text</Tab>
          <Tab>Graph</Tab>
          <Tab>Hybrid</Tab>
        </TabList>
      </Tabs>

      {error && (
        <Alert status="error" borderRadius="lg">
          <AlertIcon />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {isSearching && (
        <Box textAlign="center" py={8}>
          <Spinner size="xl" color="blue.500" thickness="3px" />
          <Text mt={4} color="gray.500">Searching...</Text>
        </Box>
      )}

      {!isSearching && results.length > 0 && (
        <VStack spacing={3} align="stretch">
          <Text fontWeight="medium" fontSize="sm" color="gray.500">
            Found {results.length} results
          </Text>
          {results.map((result) => (
            <Card
              key={result.document_id}
              cursor="pointer"
              onClick={() => onResultSelect?.(result)}
              _hover={{
                transform: 'translateY(-2px)',
                shadow: 'lg',
              }}
              transition="all 0.2s"
              bg={bgColor}
              borderWidth="1px"
              borderColor={borderColor}
            >
              <CardBody>
                <VStack align="stretch" spacing={2}>
                  <HStack justify="space-between">
                    <Text fontWeight="bold" fontSize="lg">
                      {result.metadata.name}
                    </Text>
                    <Badge colorScheme={getScoreColor(result.score)}>
                      {(result.score * 100).toFixed(1)}% match
                    </Badge>
                  </HStack>

                  <HStack spacing={2}>
                    <Badge variant="outline">{result.metadata.document_type}</Badge>
                    <Text fontSize="sm" color="gray.500">
                      {new Date(result.metadata.updated_at).toLocaleDateString()}
                    </Text>
                  </HStack>

                  {result.highlights && result.highlights.length > 0 && (
                    <Box>
                      <Text fontSize="sm" color="gray.600" noOfLines={2}>
                        ...{result.highlights[0]}...
                      </Text>
                    </Box>
                  )}

                  <Progress
                    value={result.score * 100}
                    size="xs"
                    colorScheme={getScoreColor(result.score)}
                    borderRadius="full"
                  />
                </VStack>
              </CardBody>
            </Card>
          ))}
        </VStack>
      )}

      {!isSearching && query && results.length === 0 && !error && (
        <Box textAlign="center" py={8}>
          <Text color="gray.500">No results found for "{query}"</Text>
          <Text fontSize="sm" color="gray.400" mt={2}>
            Try different keywords or search type
          </Text>
        </Box>
      )}
    </VStack>
  );
};