/**
 * ToolsMenu Component Tests
 *
 * Unit tests for the ToolsMenu component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ToolsMenu } from './ToolsMenu';
import type { DocumentMessage } from '../../types/document';
import * as toolsRegistry from '../../utils/toolsRegistry';

// Mock the toolsRegistry module
vi.mock('../../utils/toolsRegistry', async () => {
  const actual = await vi.importActual('../../utils/toolsRegistry');
  return {
    ...actual,
    getAvailableTools: vi.fn(),
  };
});

describe('ToolsMenu', () => {
  const mockDocument: DocumentMessage = {
    metadata: {
      document_id: 'doc-123',
      name: 'Test Document',
      document_type: 'pdf',
      version: 1,
      size: 1024,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
    content: {},
    tools: [],
  };

  const mockTools = [
    {
      id: 'summarize',
      label: 'Summarize',
      icon: vi.fn(() => null) as any,
      description: 'Generate summary',
      action: vi.fn().mockResolvedValue({ summary: 'Test summary' }),
      documentTypes: ['pdf', 'word'],
      requiresConfirmation: false,
    },
    {
      id: 'extract_entities',
      label: 'Extract Entities',
      icon: vi.fn(() => null) as any,
      description: 'Extract entities',
      action: vi.fn().mockResolvedValue({ entities: [] }),
      documentTypes: ['pdf'],
      requiresConfirmation: false,
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    (toolsRegistry.getAvailableTools as any).mockReturnValue(mockTools);
  });

  it('renders tools menu with title', () => {
    render(<ToolsMenu document={mockDocument} />);
    expect(screen.getByText('Tools')).toBeInTheDocument();
  });

  it('displays available tools for document type', () => {
    render(<ToolsMenu document={mockDocument} />);

    expect(screen.getByText('Summarize')).toBeInTheDocument();
    expect(screen.getByText('Extract Entities')).toBeInTheDocument();
  });

  it('shows tool count in footer', () => {
    render(<ToolsMenu document={mockDocument} />);
    expect(screen.getByText('2 tools available')).toBeInTheDocument();
  });

  it('shows singular "tool" when only one available', () => {
    (toolsRegistry.getAvailableTools as any).mockReturnValue([mockTools[0]]);
    render(<ToolsMenu document={mockDocument} />);
    expect(screen.getByText('1 tool available')).toBeInTheDocument();
  });

  it('displays empty state when no tools available', () => {
    (toolsRegistry.getAvailableTools as any).mockReturnValue([]);
    render(<ToolsMenu document={mockDocument} />);

    expect(screen.getByText('No tools available for this document type')).toBeInTheDocument();
  });

  it('marks executed tools with check icon', () => {
    const documentWithTools: DocumentMessage = {
      ...mockDocument,
      tools: ['summarize'],
    };

    render(<ToolsMenu document={documentWithTools} />);

    const summarizeButton = screen.getByText('Summarize').closest('button');
    expect(summarizeButton?.className).toContain('executed');
  });

  it('executes tool when clicked', async () => {
    const onToolExecuted = vi.fn();
    render(<ToolsMenu document={mockDocument} onToolExecuted={onToolExecuted} />);

    const summarizeButton = screen.getByText('Summarize');
    fireEvent.click(summarizeButton);

    await waitFor(() => {
      expect(mockTools[0].action).toHaveBeenCalledWith('doc-123');
      expect(onToolExecuted).toHaveBeenCalledWith('summarize', { summary: 'Test summary' });
    });
  });

  it('shows loading state during tool execution', async () => {
    const slowAction = vi.fn(
      () => new Promise((resolve) => setTimeout(() => resolve({ result: 'ok' }), 100))
    );

    const toolsWithSlowAction = [
      {
        ...mockTools[0],
        action: slowAction,
      },
    ];

    (toolsRegistry.getAvailableTools as any).mockReturnValue(toolsWithSlowAction);

    render(<ToolsMenu document={mockDocument} />);

    const summarizeButton = screen.getByText('Summarize');
    fireEvent.click(summarizeButton);

    await waitFor(() => {
      const button = screen.getByText('Summarize').closest('button');
      expect(button?.className).toContain('executing');
    });
  });

  it('disables other tools during execution', async () => {
    const slowAction = vi.fn(
      () => new Promise((resolve) => setTimeout(() => resolve({ result: 'ok' }), 100))
    );

    const toolsWithSlowAction = [
      { ...mockTools[0], action: slowAction },
      mockTools[1],
    ];

    (toolsRegistry.getAvailableTools as any).mockReturnValue(toolsWithSlowAction);

    render(<ToolsMenu document={mockDocument} />);

    const summarizeButton = screen.getByText('Summarize');
    fireEvent.click(summarizeButton);

    await waitFor(() => {
      const entitiesButton = screen.getByText('Extract Entities').closest('button');
      expect(entitiesButton).toBeDisabled();
    });
  });

  it('handles tool execution errors', async () => {
    const errorAction = vi.fn().mockRejectedValue(new Error('Tool failed'));
    const onToolError = vi.fn();

    const toolsWithError = [
      {
        ...mockTools[0],
        action: errorAction,
      },
    ];

    (toolsRegistry.getAvailableTools as any).mockReturnValue(toolsWithError);

    render(<ToolsMenu document={mockDocument} onToolError={onToolError} />);

    const summarizeButton = screen.getByText('Summarize');
    fireEvent.click(summarizeButton);

    await waitFor(() => {
      expect(screen.getByText(/Failed to execute Summarize/)).toBeInTheDocument();
      expect(onToolError).toHaveBeenCalledWith(
        'summarize',
        expect.any(Error)
      );
    });
  });

  it('shows confirmation dialog for tools requiring confirmation', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false);

    const toolsWithConfirm = [
      {
        ...mockTools[0],
        requiresConfirmation: true,
      },
    ];

    (toolsRegistry.getAvailableTools as any).mockReturnValue(toolsWithConfirm);

    render(<ToolsMenu document={mockDocument} />);

    const summarizeButton = screen.getByText('Summarize');
    fireEvent.click(summarizeButton);

    await waitFor(() => {
      expect(confirmSpy).toHaveBeenCalled();
      expect(mockTools[0].action).not.toHaveBeenCalled();
    });

    confirmSpy.mockRestore();
  });

  it('executes tool when confirmation accepted', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);
    const onToolExecuted = vi.fn();

    const toolsWithConfirm = [
      {
        ...mockTools[0],
        requiresConfirmation: true,
      },
    ];

    (toolsRegistry.getAvailableTools as any).mockReturnValue(toolsWithConfirm);

    render(<ToolsMenu document={mockDocument} onToolExecuted={onToolExecuted} />);

    const summarizeButton = screen.getByText('Summarize');
    fireEvent.click(summarizeButton);

    await waitFor(() => {
      expect(confirmSpy).toHaveBeenCalled();
      expect(mockTools[0].action).toHaveBeenCalled();
      expect(onToolExecuted).toHaveBeenCalled();
    });

    confirmSpy.mockRestore();
  });

  it('prevents concurrent tool executions', async () => {
    const slowAction = vi.fn(
      () => new Promise((resolve) => setTimeout(() => resolve({ result: 'ok' }), 200))
    );

    const toolsWithSlowAction = [
      {
        ...mockTools[0],
        action: slowAction,
      },
    ];

    (toolsRegistry.getAvailableTools as any).mockReturnValue(toolsWithSlowAction);

    render(<ToolsMenu document={mockDocument} />);

    const summarizeButton = screen.getByText('Summarize');

    // Click multiple times rapidly
    fireEvent.click(summarizeButton);
    fireEvent.click(summarizeButton);
    fireEvent.click(summarizeButton);

    // Wait for execution to complete
    await waitFor(() => {
      expect(slowAction).toHaveBeenCalledTimes(1);
    }, { timeout: 1000 });
  });

  it('displays JSON-specific tools for JSON documents', () => {
    const jsonDocument: DocumentMessage = {
      ...mockDocument,
      metadata: {
        ...mockDocument.metadata,
        document_type: 'json',
      },
    };

    const jsonTools = [
      {
        id: 'validate_json',
        label: 'Validate JSON',
        icon: vi.fn(() => null) as any,
        description: 'Validate JSON structure',
        action: vi.fn().mockResolvedValue({ valid: true }),
        documentTypes: ['json'],
        requiresConfirmation: false,
      },
      {
        id: 'format_json',
        label: 'Format JSON',
        icon: vi.fn(() => null) as any,
        description: 'Format JSON',
        action: vi.fn().mockResolvedValue({ formatted: true }),
        documentTypes: ['json'],
        requiresConfirmation: false,
      },
    ];

    (toolsRegistry.getAvailableTools as any).mockReturnValue(jsonTools);

    render(<ToolsMenu document={jsonDocument} />);

    expect(screen.getByText('Validate JSON')).toBeInTheDocument();
    expect(screen.getByText('Format JSON')).toBeInTheDocument();
  });

  it('shows default tools when no specific tools available', () => {
    const unknownDocument: DocumentMessage = {
      ...mockDocument,
      metadata: {
        ...mockDocument.metadata,
        document_type: 'unknown',
      },
    };

    const defaultTools = [
      mockTools[0], // summarize
      mockTools[1], // extract_entities
    ];

    (toolsRegistry.getAvailableTools as any).mockReturnValue(defaultTools);

    render(<ToolsMenu document={unknownDocument} />);

    expect(screen.getByText('Summarize')).toBeInTheDocument();
    expect(screen.getByText('Extract Entities')).toBeInTheDocument();
  });
});
