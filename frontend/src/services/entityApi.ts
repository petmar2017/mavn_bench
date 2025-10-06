/**
 * Entity API Service
 *
 * Provides methods for interacting with entity-related API endpoints
 */

import { API_BASE_URL } from '../config/api.config';
import type { Entity, EntityRelationship } from '../types/document';

export interface EntityTypesResponse {
  types: string[];
}

export interface RelationshipTypesResponse {
  types: string[];
}

export interface DocumentEntitiesResponse {
  document_id: string;
  entities: Entity[];
  relationships: EntityRelationship[];
}

export interface UpdateDocumentEntitiesRequest {
  entities: Entity[];
  relationships: EntityRelationship[];
}

class EntityApiService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_BASE_URL;
  }

  /**
   * Get available entity types
   */
  async getEntityTypes(): Promise<string[]> {
    const response = await fetch(`${this.baseUrl}/api/entities/types`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch entity types: ${response.statusText}`);
    }

    const data: EntityTypesResponse = await response.json();
    return data.types;
  }

  /**
   * Get available relationship types
   */
  async getRelationshipTypes(): Promise<string[]> {
    const response = await fetch(`${this.baseUrl}/api/entities/relationship-types`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch relationship types: ${response.statusText}`);
    }

    const data: RelationshipTypesResponse = await response.json();
    return data.types;
  }

  /**
   * Get entities and relationships for a document
   */
  async getDocumentEntities(documentId: string): Promise<DocumentEntitiesResponse> {
    const response = await fetch(`${this.baseUrl}/api/entities/document/${documentId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch document entities: ${response.statusText}`);
    }

    return await response.json();
  }

  /**
   * Update entities and relationships for a document
   */
  async updateDocumentEntities(
    documentId: string,
    entities: Entity[],
    relationships: EntityRelationship[]
  ): Promise<DocumentEntitiesResponse> {
    const request: UpdateDocumentEntitiesRequest = {
      entities,
      relationships,
    };

    const response = await fetch(`${this.baseUrl}/api/entities/document/${documentId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Failed to update document entities: ${response.statusText}`);
    }

    return await response.json();
  }
}

export const entityApi = new EntityApiService();
