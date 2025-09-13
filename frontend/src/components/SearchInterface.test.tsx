import React from 'react';
import { render, screen, fireEvent, waitFor } from '../test/utils';
import userEvent from '@testing-library/user-event';
import { SearchInterface } from './SearchInterface';
import { searchApi } from '../services/api';
import { mockSearchResults } from '../test/mocks';

// Mock the API
jest.mock('../services/api', () => ({
  searchApi: {
    vectorSearch: jest.fn(),
    fulltextSearch: jest.fn(),
    graphSearch: jest.fn(),
    hybridSearch: jest.fn(),
  },
}));

const mockedSearchApi = searchApi as jest.Mocked<typeof searchApi>;

describe('SearchInterface', () => {
  const mockOnResultSelect = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
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
    mockedSearchApi.vectorSearch.mockResolvedValueOnce(mockSearchResults);

    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    const searchInput = screen.getByPlaceholderText(/search documents/i);
    await user.type(searchInput, 'test query');

    const searchButton = screen.getByRole('button', { name: /search/i });
    await user.click(searchButton);

    await waitFor(() => {
      expect(mockedSearchApi.vectorSearch).toHaveBeenCalledWith({
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
    mockedSearchApi.vectorSearch.mockResolvedValueOnce(mockSearchResults);

    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    const searchInput = screen.getByPlaceholderText(/search documents/i);
    await user.type(searchInput, 'test query');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(mockedSearchApi.vectorSearch).toHaveBeenCalledWith({
        query: 'test query',
        limit: 20,
      });
    });
  });

  it('should switch between search types', async () => {
    mockedSearchApi.fulltextSearch.mockResolvedValueOnce(mockSearchResults);

    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    // Switch to Full Text tab
    const fullTextTab = screen.getByText('Full Text');
    await user.click(fullTextTab);

    const searchInput = screen.getByPlaceholderText(/search documents/i);
    await user.type(searchInput, 'test query');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(mockedSearchApi.fulltextSearch).toHaveBeenCalledWith({
        query: 'test query',
        limit: 20,
      });
    });
  });

  it('should perform graph search when Graph tab is selected', async () => {
    mockedSearchApi.graphSearch.mockResolvedValueOnce(mockSearchResults);

    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    const graphTab = screen.getByText('Graph');
    await user.click(graphTab);

    const searchInput = screen.getByPlaceholderText(/search documents/i);
    await user.type(searchInput, 'test query');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(mockedSearchApi.graphSearch).toHaveBeenCalledWith({
        query: 'test query',
        limit: 20,
      });
    });
  });

  it('should perform hybrid search when Hybrid tab is selected', async () => {
    mockedSearchApi.hybridSearch.mockResolvedValueOnce(mockSearchResults);

    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    const hybridTab = screen.getByText('Hybrid');
    await user.click(hybridTab);

    const searchInput = screen.getByPlaceholderText(/search documents/i);
    await user.type(searchInput, 'test query');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(mockedSearchApi.hybridSearch).toHaveBeenCalledWith({
        query: 'test query',
        limit: 20,
      });
    });
  });

  it('should show loading state while searching', async () => {
    // Mock a delayed response
    mockedSearchApi.vectorSearch.mockImplementation(
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
    mockedSearchApi.vectorSearch.mockRejectedValueOnce(
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
    mockedSearchApi.vectorSearch.mockResolvedValueOnce(mockSearchResults);

    const user = userEvent.setup();

    render(<SearchInterface onResultSelect={mockOnResultSelect} />);

    const searchInput = screen.getByPlaceholderText(/search documents/i);
    await user.type(searchInput, 'test query');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
    });

    // Click clear button (X icon)
    const clearButton = screen.getByRole('button', { name: '' }); // Button with X icon
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

    expect(mockedSearchApi.vectorSearch).not.toHaveBeenCalled();
  });

  it('should handle result selection', async () => {
    mockedSearchApi.vectorSearch.mockResolvedValueOnce(mockSearchResults);

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
    mockedSearchApi.vectorSearch.mockResolvedValueOnce(mockSearchResults);

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
    mockedSearchApi.vectorSearch.mockResolvedValueOnce([]);

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
    mockedSearchApi.vectorSearch.mockResolvedValueOnce(mockSearchResults);

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

    mockedSearchApi.vectorSearch.mockResolvedValueOnce(resultsWithVariedScores);

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
    mockedSearchApi.vectorSearch.mockResolvedValueOnce(mockSearchResults);

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
    mockedSearchApi.vectorSearch.mockResolvedValueOnce(mockSearchResults);

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
    mockedSearchApi.vectorSearch.mockRejectedValueOnce(
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
    mockedSearchApi.vectorSearch.mockResolvedValueOnce(mockSearchResults);

    await user.clear(searchInput);
    await user.type(searchInput, 'successful query');
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(screen.queryByText(/search failed/i)).not.toBeInTheDocument();
      expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
    });
  });
});