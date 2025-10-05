/**
 * Tools Registry for Mavn Bench
 *
 * Manages available document processing tools and their metadata.
 * Provides context-sensitive tool discovery based on document type.
 *
 * @module utils/toolsRegistry
 */

import { FileText, Tag, MessageSquare, Languages, Search } from 'lucide-react';
import { processApi } from '../services/api';
import type { ComponentType } from 'react';

/**
 * Tool definition interface
 */
export interface ToolDefinition {
  /** Unique tool identifier */
  id: string;
  /** Display label for UI */
  label: string;
  /** Icon component from lucide-react */
  icon: ComponentType<{ size?: number }>;
  /** Tool execution function */
  action: (documentId: string) => Promise<any>;
  /** Document types that support this tool */
  documentTypes: string[];
  /** Optional description */
  description?: string;
  /** Whether tool requires user confirmation */
  requiresConfirmation?: boolean;
}

/**
 * Registry of available tools
 * Each tool is mapped to its definition
 */
export const AVAILABLE_TOOLS: Record<string, ToolDefinition> = {
  summarize: {
    id: 'summarize',
    label: 'Summarize',
    icon: FileText,
    description: 'Generate a summary of the document content',
    action: async (documentId: string) => {
      const result = await processApi.summarize(documentId);
      return result;
    },
    documentTypes: ['pdf', 'word', 'markdown', 'text', 'webpage', 'youtube', 'podcast'],
    requiresConfirmation: false,
  },
  extract_entities: {
    id: 'extract_entities',
    label: 'Extract Entities',
    icon: Tag,
    description: 'Extract named entities (people, places, organizations)',
    action: async (documentId: string) => {
      const result = await processApi.extractEntities(documentId);
      return result;
    },
    documentTypes: ['pdf', 'word', 'markdown', 'text', 'webpage'],
    requiresConfirmation: false,
  },
  qa: {
    id: 'qa',
    label: 'Q&A',
    icon: MessageSquare,
    description: 'Ask questions about the document',
    action: async (documentId: string) => {
      // This would open a Q&A interface
      // For now, it's a placeholder
      return { message: 'Q&A interface not yet implemented' };
    },
    documentTypes: ['pdf', 'word', 'markdown', 'text', 'webpage', 'youtube', 'podcast'],
    requiresConfirmation: false,
  },
  detect_language: {
    id: 'detect_language',
    label: 'Detect Language',
    icon: Languages,
    description: 'Detect the language of the document',
    action: async (documentId: string) => {
      // Placeholder for language detection
      return { message: 'Language detection not yet implemented' };
    },
    documentTypes: ['pdf', 'word', 'markdown', 'text', 'webpage'],
    requiresConfirmation: false,
  },
  find_similar: {
    id: 'find_similar',
    label: 'Find Similar',
    icon: Search,
    description: 'Find similar documents using vector search',
    action: async (documentId: string) => {
      // This would trigger a search for similar documents
      return { message: 'Find similar not yet implemented' };
    },
    documentTypes: ['pdf', 'word', 'markdown', 'text', 'webpage', 'youtube', 'podcast'],
    requiresConfirmation: false,
  },
};

/**
 * Get available tools for a specific document type
 *
 * @param documentType - The type of document (pdf, word, etc.)
 * @param executedTools - Array of tool IDs that have already been executed
 * @returns Array of tool definitions available for this document type
 */
export function getAvailableTools(
  documentType: string,
  executedTools: string[] = []
): ToolDefinition[] {
  const normalizedType = documentType.toLowerCase();

  return Object.values(AVAILABLE_TOOLS).filter((tool) =>
    tool.documentTypes.includes(normalizedType)
  );
}

/**
 * Get a specific tool definition by ID
 *
 * @param toolId - The tool identifier
 * @returns Tool definition or undefined if not found
 */
export function getTool(toolId: string): ToolDefinition | undefined {
  return AVAILABLE_TOOLS[toolId];
}

/**
 * Check if a tool has been executed on a document
 *
 * @param toolId - The tool identifier
 * @param executedTools - Array of executed tool IDs
 * @returns True if the tool has been executed
 */
export function isToolExecuted(
  toolId: string,
  executedTools: string[] = []
): boolean {
  return executedTools.includes(toolId);
}

/**
 * Get the count of available tools for a document type
 *
 * @param documentType - The type of document
 * @returns Number of available tools
 */
export function getToolCount(documentType: string): number {
  return getAvailableTools(documentType).length;
}
