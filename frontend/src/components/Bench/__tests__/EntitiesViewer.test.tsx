import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { EntitiesViewer } from '../EntitiesViewer';
import { documentApi } from '../../../services/api';
import type { Entity } from '../../../types/document';

// Mock the API
vi.mock('../../../services/api', () => ({
  documentApi: {
    updateDocument: vi.fn(),
  },
}));

// Mock logger
vi.mock('../../../services/logging', () => ({
  logger: {
    info: vi.fn(),
    error: vi.fn(),
  },
}));

describe('EntitiesViewer', () => {
  const mockDocumentId = 'doc-123';
  const mockEntities: Entity[] = [
    {
      text: 'John Doe',
      entity_type: 'PERSON',
      confidence: 0.95,
      metadata: {},
    },
    {
      text: 'Acme Corp',
      entity_type: 'ORGANIZATION',
      confidence: 0.88,
      metadata: {},
    },
    {
      text: 'New York',
      entity_type: 'LOCATION',
      confidence: 0.92,
      metadata: {},
    },
    {
      text: '2024-01-15',
      entity_type: 'DATE',
      confidence: 0.85,
      metadata: {},
    },
    {
      text: '$1,000',
      entity_type: 'MONEY',
      confidence: 0.90,
      metadata: {},
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render empty state when no entities provided', () => {
      render(
        <EntitiesViewer
          documentId={mockDocumentId}
          entities={[]}
        />
      );

      expect(screen.getByText('No entities extracted yet')).toBeInTheDocument();
      expect(screen.getByText(/Use the "Extract Entities" tool/i)).toBeInTheDocument();
    });

    it('should render entities grouped by type', () => {
      render(
        <EntitiesViewer
          documentId={mockDocumentId}
          entities={mockEntities}
        />
      );

      // Check header
      expect(screen.getByText(/Extracted Entities \(5\)/i)).toBeInTheDocument();

      // Check entity type groups
      expect(screen.getByText('PERSON')).toBeInTheDocument();
      expect(screen.getByText('ORGANIZATION')).toBeInTheDocument();
      expect(screen.getByText('LOCATION')).toBeInTheDocument();
      expect(screen.getByText('DATE')).toBeInTheDocument();
      expect(screen.getByText('MONEY')).toBeInTheDocument();
    });

    it('should display entity counts for each type', () => {
      render(
        <EntitiesViewer
          documentId={mockDocumentId}
          entities={mockEntities}
        />
      );

      // Each type should show count (1)
      const countElements = screen.getAllByText('(1)');
      expect(countElements).toHaveLength(5);
    });

    it('should display entity text and confidence scores', () => {
      render(
        <EntitiesViewer
          documentId={mockDocumentId}
          entities={mockEntities}
        />
      );

      expect(screen.getByText('John Doe')).toBeInTheDocument();
      expect(screen.getByText('95% confidence')).toBeInTheDocument();
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
      expect(screen.getByText('88% confidence')).toBeInTheDocument();
    });
  });

  describe('Expand/Collapse Functionality', () => {
    it('should expand all groups by default', () => {
      render(
        <EntitiesViewer
          documentId={mockDocumentId}
          entities={mockEntities}
        />
      );

      // All entity texts should be visible
      expect(screen.getByText('John Doe')).toBeInTheDocument();
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
      expect(screen.getByText('New York')).toBeInTheDocument();
    });

    it('should collapse group when header is clicked', async () => {
      render(
        <EntitiesViewer
          documentId={mockDocumentId}
          entities={mockEntities}
        />
      );

      // Find and click the PERSON group header
      const personHeader = screen.getByText('PERSON').closest('div');
      fireEvent.click(personHeader!);

      await waitFor(() => {
        expect(screen.queryByText('John Doe')).not.toBeInTheDocument();
      });
    });

    it('should expand collapsed group when header is clicked again', async () => {
      render(
        <EntitiesViewer
          documentId={mockDocumentId}
          entities={mockEntities}
        />
      );

      const personHeader = screen.getByText('PERSON').closest('div');

      // Collapse
      fireEvent.click(personHeader!);
      await waitFor(() => {
        expect(screen.queryByText('John Doe')).not.toBeInTheDocument();
      });

      // Expand
      fireEvent.click(personHeader!);
      await waitFor(() => {
        expect(screen.getByText('John Doe')).toBeInTheDocument();
      });
    });
  });

  describe('Edit Functionality', () => {
    it('should show edit form when edit button is clicked', async () => {
      render(
        <EntitiesViewer
          documentId={mockDocumentId}
          entities={mockEntities}
        />
      );

      // Click edit button for first entity
      const editButtons = screen.getAllByTitle('Edit entity');
      fireEvent.click(editButtons[0]);

      await waitFor(() => {
        expect(screen.getByDisplayValue('John Doe')).toBeInTheDocument();
        expect(screen.getByDisplayValue('0.95')).toBeInTheDocument();
      });
    });

    it('should allow editing entity text', async () => {
      render(
        <EntitiesViewer
          documentId={mockDocumentId}
          entities={mockEntities}
        />
      );

      const editButtons = screen.getAllByTitle('Edit entity');
      fireEvent.click(editButtons[0]);

      const textInput = screen.getByDisplayValue('John Doe');
      fireEvent.change(textInput, { target: { value: 'Jane Smith' } });

      expect(screen.getByDisplayValue('Jane Smith')).toBeInTheDocument();
    });

    it('should allow changing entity type', async () => {
      const { container } = render(
        <EntitiesViewer
          documentId={mockDocumentId}
          entities={mockEntities}
        />
      );

      const editButtons = screen.getAllByTitle('Edit entity');
      fireEvent.click(editButtons[0]);

      // Find the select element
      const typeSelect = container.querySelector('select') as HTMLSelectElement;
      expect(typeSelect).toBeInTheDocument();
      expect(typeSelect.value).toBe('PERSON');

      fireEvent.change(typeSelect, { target: { value: 'ORGANIZATION' } });

      expect(typeSelect.value).toBe('ORGANIZATION');
    });

    it('should allow adjusting confidence score', async () => {
      render(
        <EntitiesViewer
          documentId={mockDocumentId}
          entities={mockEntities}
        />
      );

      const editButtons = screen.getAllByTitle('Edit entity');
      fireEvent.click(editButtons[0]);

      const confidenceInput = screen.getByDisplayValue('0.95');
      fireEvent.change(confidenceInput, { target: { value: '0.85' } });

      expect(screen.getByDisplayValue('0.85')).toBeInTheDocument();
    });

    it('should cancel edit without saving when cancel is clicked', async () => {
      render(
        <EntitiesViewer
          documentId={mockDocumentId}
          entities={mockEntities}
        />
      );

      const editButtons = screen.getAllByTitle('Edit entity');
      fireEvent.click(editButtons[0]);

      // Change value
      const textInput = screen.getByDisplayValue('John Doe');
      fireEvent.change(textInput, { target: { value: 'Jane Smith' } });

      // Click cancel
      const cancelButton = screen.getByText('Cancel');
      fireEvent.click(cancelButton);

      await waitFor(() => {
        expect(screen.queryByDisplayValue('Jane Smith')).not.toBeInTheDocument();
        expect(screen.getByText('John Doe')).toBeInTheDocument();
      });
    });
  });

  describe('Save Functionality', () => {
    it('should save entity changes and update document', async () => {
      vi.mocked(documentApi.updateDocument).mockResolvedValueOnce({} as any);

      const onEntitiesUpdate = vi.fn();

      render(
        <EntitiesViewer
          documentId={mockDocumentId}
          entities={mockEntities}
          onEntitiesUpdate={onEntitiesUpdate}
        />
      );

      const editButtons = screen.getAllByTitle('Edit entity');
      fireEvent.click(editButtons[0]);

      // Change entity text
      const textInput = screen.getByDisplayValue('John Doe');
      fireEvent.change(textInput, { target: { value: 'Jane Smith' } });

      // Click save
      const saveButton = screen.getByText('Save');
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(documentApi.updateDocument).toHaveBeenCalledWith(
          mockDocumentId,
          {
            metadata: {
              entities: expect.arrayContaining([
                expect.objectContaining({
                  text: 'Jane Smith',
                  entity_type: 'PERSON',
                  confidence: 0.95,
                }),
              ]),
            },
          }
        );
      });

      expect(onEntitiesUpdate).toHaveBeenCalled();
    });

    it('should show saving state during save operation', async () => {
      vi.mocked(documentApi.updateDocument).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve({} as any), 100))
      );

      render(
        <EntitiesViewer
          documentId={mockDocumentId}
          entities={mockEntities}
        />
      );

      const editButtons = screen.getAllByTitle('Edit entity');
      fireEvent.click(editButtons[0]);

      const saveButton = screen.getByText('Save');
      fireEvent.click(saveButton);

      expect(screen.getByText('Saving...')).toBeInTheDocument();

      await waitFor(() => {
        expect(screen.queryByText('Saving...')).not.toBeInTheDocument();
      });
    });

    it('should handle save errors gracefully', async () => {
      vi.mocked(documentApi.updateDocument).mockRejectedValueOnce(
        new Error('Failed to save')
      );

      // Mock window.alert
      const alertMock = vi.spyOn(window, 'alert').mockImplementation(() => {});

      render(
        <EntitiesViewer
          documentId={mockDocumentId}
          entities={mockEntities}
        />
      );

      const editButtons = screen.getAllByTitle('Edit entity');
      fireEvent.click(editButtons[0]);

      const textInput = screen.getByDisplayValue('John Doe');
      fireEvent.change(textInput, { target: { value: 'Jane Smith' } });

      const saveButton = screen.getByText('Save');
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(alertMock).toHaveBeenCalledWith('Failed to save entity changes');
      });

      alertMock.mockRestore();
    });
  });

  describe('Entity Grouping', () => {
    it('should group multiple entities of same type together', () => {
      const multiplePersons: Entity[] = [
        { text: 'John Doe', entity_type: 'PERSON', confidence: 0.95, metadata: {} },
        { text: 'Jane Smith', entity_type: 'PERSON', confidence: 0.90, metadata: {} },
        { text: 'Bob Johnson', entity_type: 'PERSON', confidence: 0.88, metadata: {} },
      ];

      render(
        <EntitiesViewer
          documentId={mockDocumentId}
          entities={multiplePersons}
        />
      );

      expect(screen.getByText('(3)')).toBeInTheDocument();
      expect(screen.getByText('John Doe')).toBeInTheDocument();
      expect(screen.getByText('Jane Smith')).toBeInTheDocument();
      expect(screen.getByText('Bob Johnson')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA attributes', () => {
      render(
        <EntitiesViewer
          documentId={mockDocumentId}
          entities={mockEntities}
        />
      );

      // Edit buttons should have titles
      const editButtons = screen.getAllByTitle('Edit entity');
      expect(editButtons.length).toBeGreaterThan(0);
    });
  });
});
