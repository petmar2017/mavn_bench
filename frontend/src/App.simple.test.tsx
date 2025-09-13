import React from 'react';
import { render, screen } from './test/utils';
import App from './App';

// Mock the services to avoid complex setup
jest.mock('./services/websocket', () => ({
  wsService: {
    connect: jest.fn(),
    disconnect: jest.fn(),
    onSystemNotification: jest.fn(() => jest.fn()),
  },
}));

jest.mock('./services/api', () => ({
  documentApi: {
    createDocument: jest.fn(),
    listDocuments: jest.fn(() => Promise.resolve([])),
    deleteDocument: jest.fn(),
  },
  searchApi: {
    vectorSearch: jest.fn(() => Promise.resolve([])),
    fulltextSearch: jest.fn(() => Promise.resolve([])),
    graphSearch: jest.fn(() => Promise.resolve([])),
    hybridSearch: jest.fn(() => Promise.resolve([])),
  },
}));

describe('App Component', () => {
  it('should render the app with header', () => {
    render(<App />);

    expect(screen.getByText('Mavn Bench')).toBeInTheDocument();
    expect(screen.getByText('Document Processing Platform')).toBeInTheDocument();
  });

  it('should render all three tabs', () => {
    render(<App />);

    expect(screen.getByText('Upload')).toBeInTheDocument();
    expect(screen.getByText('Documents')).toBeInTheDocument();
    expect(screen.getByText('Search')).toBeInTheDocument();
  });

  it('should render the dark mode toggle', () => {
    render(<App />);

    const toggleButton = screen.getByLabelText(/toggle color mode/i);
    expect(toggleButton).toBeInTheDocument();
  });
});