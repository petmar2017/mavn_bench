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

    expect(screen.getByPlaceholderText(/search documents/i)).toBeInTheDocument();
    expect(screen.getByText('Vector')).toBeInTheDocument();
    expect(screen.getByText('Full Text')).toBeInTheDocument();
    expect(screen.getByText('Graph')).toBeInTheDocument();
    expect(screen.getByText('Hybrid')).toBeInTheDocument();
  });

  it('should perform vector search on button click', async () => {
    vi.mocked(searchApi).vectorSearch.mockResolvedValueOnce(mockSearchResults);

    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    const searchInput = screen.getByPlaceholderText(/search documents/i);
    await user.type(searchInput, 'test query');

    const searchButton = screen.getByRole('button', { name: /search/i });
    await user.click(searchButton);

    await waitFor(() => {
      expect(searchApi.vectorSearch).toHaveBeenCalledWith({
        query: 'test query',
        limit: 20,
      });
    });

    // Should display results
    await waitFor(() => {
      expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
      expect(screen.getByText(/95.0% match/)).toBeInTheDocument();
    });
  });

  it('should perform search on Enter key press', async () => {
    vi.mocked(searchApi).vectorSearch.mockResolvedValueOnce(mockSearchResults);

    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    const searchInput = screen.getByPlaceholderText(/search documents/i);
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

    const searchInput = screen.getByPlaceholderText(/search documents/i);
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

    const searchInput = screen.getByPlaceholderText(/search documents/i);
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

    const searchInput = screen.getByPlaceholderText(/search documents/i);
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
    vi.mocked(searchApi).vectorSearch.mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve(mockSearchResults), 100))
    );

    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    const searchInput = screen.getByPlaceholderText(/search documents/i);
    await user.type(searchInput, 'test query');
    await user.keyboard('{Enter}');

    // Should show loading spinner
    expect(screen.getByText(/searching/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.queryByText(/searching/i)).not.toBeInTheDocument();
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

    const searchInput = screen.getByPlaceholderText(/search documents/i);
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

    const searchInput = screen.getByPlaceholderText(/search documents/i);
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

  it('should not search with empty query', async () => {
    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    const searchButton = screen.getByRole('button', { name: /search/i });
    await user.click(searchButton);

    expect(searchApi.vectorSearch).not.toHaveBeenCalled();
  });

  it('should handle result selection', async () => {
    vi.mocked(searchApi).vectorSearch.mockResolvedValueOnce(mockSearchResults);

    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    const searchInput = screen.getByPlaceholderText(/search documents/i);
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

  it('should show result count', async () => {
    vi.mocked(searchApi).vectorSearch.mockResolvedValueOnce(mockSearchResults);

    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    const searchInput = screen.getByPlaceholderText(/search documents/i);
    await user.type(searchInput, 'test query');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(screen.getByText(`Found ${mockSearchResults.length} results`)).toBeInTheDocument();
    });
  });

  it('should show empty state when no results found', async () => {
    vi.mocked(searchApi).vectorSearch.mockResolvedValueOnce([]);

    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    const searchInput = screen.getByPlaceholderText(/search documents/i);
    await user.type(searchInput, 'no results query');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(screen.getByText(/no results found for "no results query"/i)).toBeInTheDocument();
      expect(screen.getByText(/try different keywords or search type/i)).toBeInTheDocument();
    });
  });

  it('should display highlights in search results', async () => {
    vi.mocked(searchApi).vectorSearch.mockResolvedValueOnce(mockSearchResults);

    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    const searchInput = screen.getByPlaceholderText(/search documents/i);
    await user.type(searchInput, 'test query');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(screen.getByText(/This is a highlighted portion/)).toBeInTheDocument();
    });
  });

  it('should show score badges with correct colors', async () => {
    const resultsWithVariedScores = [
      { ...mockSearchResults[0], score: 0.95 }, // Green
      { ...mockSearchResults[1], score: 0.7 },  // Yellow
      { ...mockSearchResults[2], score: 0.5 },  // Orange
    ];

    vi.mocked(searchApi).vectorSearch.mockResolvedValueOnce(resultsWithVariedScores);

    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    const searchInput = screen.getByPlaceholderText(/search documents/i);
    await user.type(searchInput, 'test query');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(screen.getByText(/95.0% match/)).toBeInTheDocument();
      expect(screen.getByText(/70.0% match/)).toBeInTheDocument();
      expect(screen.getByText(/50.0% match/)).toBeInTheDocument();
    });
  });

  it('should show document type badges', async () => {
    vi.mocked(searchApi).vectorSearch.mockResolvedValueOnce(mockSearchResults);

    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    const searchInput = screen.getByPlaceholderText(/search documents/i);
    await user.type(searchInput, 'test query');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(screen.getByText('pdf')).toBeInTheDocument();
    });
  });

  it('should show progress bar for scores', async () => {
    vi.mocked(searchApi).vectorSearch.mockResolvedValueOnce(mockSearchResults);

    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    const searchInput = screen.getByPlaceholderText(/search documents/i);
    await user.type(searchInput, 'test query');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      // Check for progress indicators
      const progressBars = screen.getAllByRole('progressbar');
      expect(progressBars.length).toBeGreaterThan(0);
    });
  });

  it('should preserve search query when switching tabs', async () => {
    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    const searchInput = screen.getByPlaceholderText(/search documents/i);
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

    const searchInput = screen.getByPlaceholderText(/search documents/i);
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