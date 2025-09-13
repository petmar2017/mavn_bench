import { useState } from 'react';
import { Search, FileText, HardDrive } from 'lucide-react';
import classNames from 'classnames';
import { searchApi } from '../services/api';
import type { SearchResult } from '../services/api';
import { formatFileSize } from '../utils/format';
import styles from './SearchInterface.module.css';

type SearchType = 'vector' | 'fulltext' | 'graph' | 'hybrid';

interface SearchInterfaceProps {
  onResultSelect?: (result: SearchResult) => void;
}

export const SearchInterface: React.FC<SearchInterfaceProps> = ({ onResultSelect }) => {
  const [query, setQuery] = useState('');
  const [searchType, setSearchType] = useState<SearchType>('vector');
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;

    setIsSearching(true);
    setError(null);
    setHasSearched(true);

    try {
      let searchResults: SearchResult[] = [];

      switch (searchType) {
        case 'vector':
          searchResults = await searchApi.vectorSearch({ query, limit: 20 });
          break;
        case 'fulltext':
          searchResults = await searchApi.fulltextSearch({ query, limit: 20 });
          break;
        case 'graph':
          searchResults = await searchApi.graphSearch({ query, limit: 20 });
          break;
        case 'hybrid':
          searchResults = await searchApi.hybridSearch({ query, limit: 20 });
          break;
      }

      setResults(searchResults);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Search failed. Please try again.');
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const highlightQuery = (text: string) => {
    if (!query) return text;
    const parts = text.split(new RegExp(`(${query})`, 'gi'));
    return parts.map((part, index) =>
      part.toLowerCase() === query.toLowerCase() ? (
        <span key={index} className={styles.resultHighlight}>
          {part}
        </span>
      ) : (
        part
      )
    );
  };

  const getSearchTypeDescription = () => {
    switch (searchType) {
      case 'vector':
        return 'Semantic search using document embeddings';
      case 'fulltext':
        return 'Traditional keyword-based search';
      case 'graph':
        return 'Relationship-based graph search';
      case 'hybrid':
        return 'Combined vector and full-text search';
    }
  };

  return (
    <div className={styles.container}>
      {/* Search Bar */}
      <div className={styles.searchBar}>
        <input
          type="text"
          className={styles.searchInput}
          placeholder="Search your documents..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyPress={handleKeyPress}
        />
        <button
          className={styles.searchButton}
          onClick={handleSearch}
          disabled={isSearching || !query.trim()}
        >
          <Search size={18} />
          Search
        </button>
      </div>

      {/* Search Type Selector */}
      <div className={styles.searchOptions}>
        <button
          className={classNames(styles.searchTypeButton, {
            [styles.active]: searchType === 'vector',
          })}
          onClick={() => setSearchType('vector')}
        >
          Vector
        </button>
        <button
          className={classNames(styles.searchTypeButton, {
            [styles.active]: searchType === 'fulltext',
          })}
          onClick={() => setSearchType('fulltext')}
        >
          Full Text
        </button>
        <button
          className={classNames(styles.searchTypeButton, {
            [styles.active]: searchType === 'graph',
          })}
          onClick={() => setSearchType('graph')}
        >
          Graph
        </button>
        <button
          className={classNames(styles.searchTypeButton, {
            [styles.active]: searchType === 'hybrid',
          })}
          onClick={() => setSearchType('hybrid')}
        >
          Hybrid
        </button>
      </div>

      {/* Search Type Description */}
      <div className={styles.filtersSection}>
        <p style={{ fontSize: '0.875rem', color: '#718096', margin: 0 }}>
          {getSearchTypeDescription()}
        </p>
      </div>

      {/* Error Display */}
      {error && (
        <div className={styles.error} style={{ backgroundColor: '#fff5f5', border: '1px solid #feb2b2', padding: '0.75rem', borderRadius: '0.375rem' }}>
          <span style={{ color: '#742a2a' }}>{error}</span>
        </div>
      )}

      {/* Loading State */}
      {isSearching && (
        <div className={styles.loading}>
          <div className={styles.spinner} />
        </div>
      )}

      {/* Results */}
      {!isSearching && results.length > 0 && (
        <div className={styles.results}>
          {results.map((result, index) => (
            <div
              key={result.document_id || index}
              className={styles.resultCard}
              onClick={() => onResultSelect?.(result)}
            >
              <div className={styles.resultHeader}>
                <FileText size={20} className={styles.resultIcon} />
                <div className={styles.resultTitle}>
                  {result.metadata?.name || `Document ${index + 1}`}
                </div>
                {result.score && (
                  <div className={styles.resultScore}>
                    {(result.score * 100).toFixed(0)}% match
                  </div>
                )}
              </div>

              {result.highlights && result.highlights.length > 0 && (
                <div className={styles.resultExcerpt}>
                  {highlightQuery(result.highlights[0])}
                </div>
              )}

              {result.metadata && (
                <div className={styles.resultMetadata}>
                  {result.metadata.document_type && (
                    <span>Type: {result.metadata.document_type}</span>
                  )}
                  {result.metadata.size !== undefined && (
                    <span style={{ marginLeft: '1rem', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                      <HardDrive size={14} />
                      {formatFileSize(result.metadata.size)}
                    </span>
                  )}
                  {result.metadata.created_at && (
                    <span>
                      {new Date(result.metadata.created_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* No Results */}
      {!isSearching && hasSearched && results.length === 0 && !error && (
        <div className={styles.noResults}>
          <Search size={48} className={styles.noResultsIcon} />
          <div className={styles.noResultsTitle}>No results found</div>
          <div className={styles.noResultsText}>
            Try a different search term or search type
          </div>
        </div>
      )}
    </div>
  );
};