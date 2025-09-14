import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '../test/utils';
import userEvent from '@testing-library/user-event';
import { SearchInterface } from './SearchInterface';
import { searchApi } from '../services/api';
import { mockSearchResults } from '../test/mocks';

// Mock the API
vi.mock('../services/api', () => ({
  searchApi: {
    vectorSearch: vi.fn(),
    fulltextSearch: vi.fn(),
    graphSearch: vi.fn(),
    hybridSearch: vi.fn(),
  },
}));

describe('SearchInterface', () => {
  const mockOnResultSelect = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render search input and tabs', () => {
    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    expect(screen.getByPlaceholderText('Search your documents... (Press Enter to search)')).toBeInTheDocument();
    expect(screen.getByText('Vector')).toBeInTheDocument();
    expect(screen.getByText('Full Text')).toBeInTheDocument();
    expect(screen.getByText('Graph')).toBeInTheDocument();
    expect(screen.getByText('Hybrid')).toBeInTheDocument();
  });

  it('should perform vector search on Enter key', async () => {
    vi.mocked(searchApi).vectorSearch.mockResolvedValueOnce(mockSearchResults);

    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    const searchInput = screen.getByPlaceholderText('Search your documents... (Press Enter to search)');
    await user.type(searchInput, 'test query');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(searchApi.vectorSearch).toHaveBeenCalledWith({
        query: 'test query',
        limit: 20,
      });
    });

    // Should display results
    await waitFor(() => {
      expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
      expect(screen.getByText('95% match')).toBeInTheDocument();
    });
  });

  it('should perform search on Enter key press', async () => {
    vi.mocked(searchApi).vectorSearch.mockResolvedValueOnce(mockSearchResults);

    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    const searchInput = screen.getByPlaceholderText('Search your documents... (Press Enter to search)');
    await user.type(searchInput, 'test query');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(searchApi.vectorSearch).toHaveBeenCalledWith({
        query: 'test query',
        limit: 20,
      });
    });
  });

  it('should switch between search types', async () => {
    vi.mocked(searchApi).fulltextSearch.mockResolvedValueOnce(mockSearchResults);

    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    // Switch to Full Text tab
    const fullTextTab = screen.getByText('Full Text');
    await user.click(fullTextTab);

    const searchInput = screen.getByPlaceholderText('Search your documents... (Press Enter to search)');
    await user.type(searchInput, 'test query');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(searchApi.fulltextSearch).toHaveBeenCalledWith({
        query: 'test query',
        limit: 20,
      });
    });
  });

  it('should perform graph search when Graph tab is selected', async () => {
    vi.mocked(searchApi).graphSearch.mockResolvedValueOnce(mockSearchResults);

    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    const graphTab = screen.getByText('Graph');
    await user.click(graphTab);

    const searchInput = screen.getByPlaceholderText('Search your documents... (Press Enter to search)');
    await user.type(searchInput, 'test query');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(searchApi.graphSearch).toHaveBeenCalledWith({
        query: 'test query',
        limit: 20,
      });
    });
  });

  it('should perform hybrid search when Hybrid tab is selected', async () => {
    vi.mocked(searchApi).hybridSearch.mockResolvedValueOnce(mockSearchResults);

    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    const hybridTab = screen.getByText('Hybrid');
    await user.click(hybridTab);

    const searchInput = screen.getByPlaceholderText('Search your documents... (Press Enter to search)');
    await user.type(searchInput, 'test query');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(searchApi.hybridSearch).toHaveBeenCalledWith({
        query: 'test query',
        limit: 20,
      });
    });
  });

  it('should show loading state while searching', async () => {
    // Mock a delayed response
    let resolveSearch: (value: any) => void;
    const searchPromise = new Promise((resolve) => {
      resolveSearch = resolve;
    });
    vi.mocked(searchApi).vectorSearch.mockReturnValueOnce(searchPromise);

    const user = userEvent.setup();

    const { container } = render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    const searchInput = screen.getByPlaceholderText('Search your documents... (Press Enter to search)');
    await user.type(searchInput, 'test query');
    await user.keyboard('{Enter}');

    // Should show loading spinner - use container query with CSS module class
    await waitFor(() => {
      const spinner = container.querySelector('[class*="spinner"]');
      expect(spinner).toBeInTheDocument();
    });

    // Resolve the search
    resolveSearch!(mockSearchResults);

    await waitFor(() => {
      expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
    });
  });

  it('should handle search errors', async () => {
    const errorMessage = 'Search failed. Please try again.';
    vi.mocked(searchApi).vectorSearch.mockRejectedValueOnce(
      { response: { data: { detail: errorMessage } } }
    );

    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    const searchInput = screen.getByPlaceholderText('Search your documents... (Press Enter to search)');
    await user.type(searchInput, 'test query');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });
  });

  it('should clear search results when clear button is clicked', async () => {
    vi.mocked(searchApi).vectorSearch.mockResolvedValueOnce(mockSearchResults);

    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    const searchInput = screen.getByPlaceholderText('Search your documents... (Press Enter to search)');
    await user.type(searchInput, 'test query');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
    });

    // Click clear button (X icon)
    const clearButton = screen.getByRole('button', { name: /clear search/i });
    await user.click(clearButton);

    // Results should be cleared
    expect(screen.queryByText('test-document.pdf')).not.toBeInTheDocument();
    expect(searchInput).toHaveValue('');
  });

  it('should show reset button only when there is a query or search has been performed', async () => {
    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    // Initially, reset button should not be visible
    expect(screen.queryByRole('button', { name: /clear search/i })).not.toBeInTheDocument();

    // Type in search input
    const searchInput = screen.getByPlaceholderText('Search your documents... (Press Enter to search)');
    await user.type(searchInput, 'test');

    // Reset button should appear when there's text
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /clear search/i })).toBeInTheDocument();
    });

    // Click reset button
    await user.click(screen.getByRole('button', { name: /clear search/i }));

    // Reset button should disappear when query is cleared
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /clear search/i })).not.toBeInTheDocument();
    });
  });

  it('should reset all search state when reset button is clicked', async () => {
    vi.mocked(searchApi).vectorSearch.mockResolvedValueOnce(mockSearchResults);

    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    // Perform a search
    const searchInput = screen.getByPlaceholderText('Search your documents... (Press Enter to search)');
    await user.type(searchInput, 'test query');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
    });

    // Click reset button
    const resetButton = screen.getByRole('button', { name: /clear search/i });
    await user.click(resetButton);

    // Verify all state is reset
    await waitFor(() => {
      // Query should be cleared
      expect(searchInput).toHaveValue('');
      // Results should be cleared
      expect(screen.queryByText('test-document.pdf')).not.toBeInTheDocument();
      // Results should be gone
      expect(screen.queryByText('test-document.pdf')).not.toBeInTheDocument();
      // Reset button should be hidden
      expect(screen.queryByRole('button', { name: /clear search/i })).not.toBeInTheDocument();
    });
  });

  it('should not search with empty query', async () => {
    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    const searchInput = screen.getByPlaceholderText('Search your documents... (Press Enter to search)');
    // Don't type anything, just press Enter
    await user.click(searchInput);
    await user.keyboard('{Enter}');

    expect(searchApi.vectorSearch).not.toHaveBeenCalled();
  });

  it('should handle result selection', async () => {
    vi.mocked(searchApi).vectorSearch.mockResolvedValueOnce(mockSearchResults);

    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    const searchInput = screen.getByPlaceholderText('Search your documents... (Press Enter to search)');
    await user.type(searchInput, 'test query');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
    });

    // Click on a result card
    const resultCard = screen.getByText('test-document.pdf').closest('div[role="group"]') ||
                      screen.getByText('test-document.pdf').closest('div');

    if (resultCard) {
      await user.click(resultCard);
      expect(mockOnResultSelect).toHaveBeenCalledWith(mockSearchResults[0]);
    }
  });

  it('should call onResultSelect with correct document data when search result is clicked', async () => {
    const mockDocumentData = {
      document_id: 'doc-123',
      metadata: {
        name: 'important-file.pdf',
        document_type: 'pdf',
        size: 2048,
        created_at: '2024-01-15T10:00:00Z'
      },
      content: {
        text: 'This is the document content that will show in the bench'
      },
      score: 0.95,
      highlights: ['This is a highlighted portion of the document']
    };

    vi.mocked(searchApi).vectorSearch.mockResolvedValueOnce([mockDocumentData]);

    const user = userEvent.setup();
    const onResultSelectSpy = vi.fn();

    render(<SearchInterface onResultSelect={onResultSelectSpy} />);

    // Perform search
    const searchInput = screen.getByPlaceholderText('Search your documents... (Press Enter to search)');
    await user.type(searchInput, 'important');
    await user.keyboard('{Enter}');

    // Wait for results
    await waitFor(() => {
      expect(screen.getByText('important-file.pdf')).toBeInTheDocument();
    });

    // Click on the result to select it
    const resultCard = screen.getByText('important-file.pdf').closest('div');
    if (resultCard) {
      await user.click(resultCard);
    }

    // Verify onResultSelect was called with the correct document data
    expect(onResultSelectSpy).toHaveBeenCalledTimes(1);
    expect(onResultSelectSpy).toHaveBeenCalledWith(mockDocumentData);

    // The callback should receive the full document data that can be used to display in the bench
    const callArgument = onResultSelectSpy.mock.calls[0][0];
    expect(callArgument).toHaveProperty('document_id', 'doc-123');
    expect(callArgument).toHaveProperty('metadata.name', 'important-file.pdf');
    expect(callArgument).toHaveProperty('content.text');
  });

  it('should show search results', async () => {
    vi.mocked(searchApi).vectorSearch.mockResolvedValueOnce(mockSearchResults);

    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    const searchInput = screen.getByPlaceholderText('Search your documents... (Press Enter to search)');
    await user.type(searchInput, 'test query');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      // Verify all results are displayed
      mockSearchResults.forEach(result => {
        expect(screen.getByText(result.metadata.name)).toBeInTheDocument();
      });
    });
  });

  it('should show empty state when no results found', async () => {
    vi.mocked(searchApi).vectorSearch.mockResolvedValueOnce([]);

    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    const searchInput = screen.getByPlaceholderText('Search your documents... (Press Enter to search)');
    await user.type(searchInput, 'no results query');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(screen.getByText('No results found')).toBeInTheDocument();
      expect(screen.getByText('Try a different search term or search type')).toBeInTheDocument();
    });
  });

  it('should display highlights in search results', async () => {
    vi.mocked(searchApi).vectorSearch.mockResolvedValueOnce(mockSearchResults);

    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    const searchInput = screen.getByPlaceholderText('Search your documents... (Press Enter to search)');
    await user.type(searchInput, 'test query');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      // Check that highlights are displayed for the first result
      const highlights = screen.getAllByText((content, element) => {
        return content.includes('This is a highlighted portion');
      });
      expect(highlights.length).toBeGreaterThan(0);
    });
  });

  it('should show score badges', async () => {
    const resultsWithVariedScores = [
      { ...mockSearchResults[0], score: 0.95 },
      { ...mockSearchResults[1], score: 0.7 },
      { ...mockSearchResults[2], score: 0.5 },
    ];

    vi.mocked(searchApi).vectorSearch.mockResolvedValueOnce(resultsWithVariedScores);

    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    const searchInput = screen.getByPlaceholderText('Search your documents... (Press Enter to search)');
    await user.type(searchInput, 'test query');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(screen.getByText('95% match')).toBeInTheDocument();
      expect(screen.getByText('70% match')).toBeInTheDocument();
      expect(screen.getByText('50% match')).toBeInTheDocument();
    });
  });

  it('should show document type in metadata', async () => {
    vi.mocked(searchApi).vectorSearch.mockResolvedValueOnce(mockSearchResults);

    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    const searchInput = screen.getByPlaceholderText('Search your documents... (Press Enter to search)');
    await user.type(searchInput, 'test query');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      // First wait for results to load
      expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
    });

    // Then check for the type in metadata
    const typeElements = screen.getAllByText((content) => content.startsWith('Type:'));
    expect(typeElements.length).toBeGreaterThan(0);
    expect(typeElements[0].textContent).toContain('pdf');
  });

  it('should display search results with scores', async () => {
    vi.mocked(searchApi).vectorSearch.mockResolvedValueOnce(mockSearchResults);

    const user = userEvent.setup();

    const { container } = render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    const searchInput = screen.getByPlaceholderText('Search your documents... (Press Enter to search)');
    await user.type(searchInput, 'test query');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      // Verify that results with scores are displayed
      expect(screen.getByText('95% match')).toBeInTheDocument();
      // Verify result cards are rendered using CSS module class
      const resultCards = container.querySelectorAll('[class*="resultCard"]');
      expect(resultCards.length).toBe(mockSearchResults.length);
    });
  });

  it('should preserve search query when switching tabs', async () => {
    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    const searchInput = screen.getByPlaceholderText('Search your documents... (Press Enter to search)');
    await user.type(searchInput, 'test query');

    // Switch to Full Text tab
    const fullTextTab = screen.getByText('Full Text');
    await user.click(fullTextTab);

    // Query should still be in the input
    expect(searchInput).toHaveValue('test query');
  });

  it('should clear error when new search is performed', async () => {
    // First search fails
    vi.mocked(searchApi).vectorSearch.mockRejectedValueOnce(
      { response: { data: { detail: 'Search failed' } } }
    );

    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    const searchInput = screen.getByPlaceholderText('Search your documents... (Press Enter to search)');
    await user.type(searchInput, 'failing query');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(screen.getByText(/search failed/i)).toBeInTheDocument();
    });

    // Second search succeeds
    vi.mocked(searchApi).vectorSearch.mockResolvedValueOnce(mockSearchResults);

    await user.clear(searchInput);
    await user.type(searchInput, 'successful query');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(screen.queryByText(/search failed/i)).not.toBeInTheDocument();
      expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
    });
  });
});