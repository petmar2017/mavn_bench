/**
 * Centralized document type definitions for Mavn Bench
 *
 * This file contains all document-related TypeScript interfaces used across
 * the frontend application. It ensures consistency between components and
 * maintains a single source of truth for document data structures.
 *
 * @module types/document
 */

/**
 * Core document metadata
 * Contains all metadata fields for a document without the actual content
 */
export interface DocumentMetadata {
  document_id: string;
  name: string;
  document_type: string;
  version: number;
  size: number;
  created_at: string;
  updated_at: string;
  deleted?: boolean;
  deleted_at?: string | null;
  deleted_by?: string | null;
  user_id?: string;
  tags?: string[];
  source_url?: string;
  processing_status?: string;
  summary?: string;
  language?: string;
  entities?: Entity[];
}

/**
 * Extracted entity structure
 * Represents a named entity extracted from document content
 */
export interface Entity {
  text: string;
  entity_type: string;
  confidence: number;
  metadata?: Record<string, any>;
}

/**
 * Document content structure
 * Contains the actual content data which is lazy-loaded separately
 */
export interface DocumentContent {
  raw_content?: string;
  formatted_content?: string;
  summary?: string;
  translation?: string;
  entities?: Entity[];
  metadata?: Record<string, any>;
  embeddings?: number[];
  text?: string;
  raw_text?: string;
}

/**
 * Document version history entry
 */
export interface DocumentVersion {
  version: number;
  timestamp: string;
  user: string;
  changes: Record<string, any>;
  commit_message?: string;
}

/**
 * Complete document message
 * The core data structure passed between components
 */
export interface DocumentMessage {
  id?: string;
  metadata: DocumentMetadata;
  content: DocumentContent;
  tools?: string[];
  history?: DocumentVersion[];
  audit_log?: any[];
}

/**
 * Search result structure
 * Returned from search API endpoints
 */
export interface SearchResult {
  document_id: string;
  score: number;
  metadata: DocumentMetadata;
  highlights?: string[];
}

/**
 * Search query parameters
 */
export interface SearchQuery {
  query: string;
  limit?: number;
  offset?: number;
  threshold?: number;
  filters?: Record<string, any>;
}
