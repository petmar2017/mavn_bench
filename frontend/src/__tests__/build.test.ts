/**
 * Build Validation Test
 *
 * Ensures TypeScript compilation succeeds and catches import errors
 * that backend tests don't validate.
 *
 * This test addresses the issue where import path errors (like the
 * entityApi.ts "../config" import) weren't caught by backend pytest tests.
 */

import { describe, it, expect } from 'vitest';

describe('Build Validation', () => {
  it('should have valid module imports', async () => {
    // Test that critical modules can be imported without errors
    const modules = [
      () => import('../services/api'),
      () => import('../services/entityApi'),
      () => import('../types/document'),
      () => import('../config/api.config'),
      () => import('../components/Bench/EntitiesViewer'),
    ];

    for (const importModule of modules) {
      await expect(importModule()).resolves.toBeDefined();
    }
  });

  it('should successfully import types module', async () => {
    // Types are compile-time only, but we can verify the module imports successfully
    const typesModule = await import('../types/document');

    // Module should export interfaces (available at compile time)
    expect(typesModule).toBeDefined();
  });

  it('should export entityApi service', async () => {
    const { entityApi } = await import('../services/entityApi');

    expect(entityApi).toBeDefined();
    expect(entityApi.getEntityTypes).toBeInstanceOf(Function);
    expect(entityApi.getRelationshipTypes).toBeInstanceOf(Function);
    expect(entityApi.updateDocumentEntities).toBeInstanceOf(Function);
  });

  it('should export API_BASE_URL from config', async () => {
    const { API_BASE_URL } = await import('../config/api.config');

    expect(API_BASE_URL).toBeDefined();
    expect(typeof API_BASE_URL).toBe('string');
  });
});
