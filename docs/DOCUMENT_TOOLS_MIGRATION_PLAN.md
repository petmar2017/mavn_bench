# Document Tools Migration Plan

## Overview

This document outlines the migration plan for transitioning from hardcoded document processing functionality to the new decorator-based document tools system. The migration ensures backward compatibility while enabling dynamic tool discovery and execution.

## Current State Analysis

### Existing Hardcoded Tools

1. **LLM Service Tools** (in `/backend/src/services/llm_service.py`):
   - `summarize()` - Document summarization
   - `extract_entities()` - Entity extraction
   - `classify_content()` - Content classification
   - `generate_tags()` - Tag generation

2. **Document Service Tools** (in `/backend/src/services/document_service.py`):
   - `validate_document()` - Basic document validation
   - `extract_metadata()` - Metadata extraction

3. **API Endpoints** (hardcoded in various routers):
   - `/api/process/summarize`
   - `/api/process/extract-entities`
   - `/api/documents/{id}/validate`

## Migration Strategy

### Phase 1: Create Document Tool Wrappers (Week 1)

**Objective**: Create document tools that wrap existing LLM service methods

#### 1.1 Create Wrapper Tools

Create document tools that delegate to existing LLM service methods:

```python
# backend/src/services/document_tools/tools/summarize_tool.py
@register_document_tool(DocumentToolType.SUMMARIZE)
class SummarizeTool(BaseDocumentTool):
    """Wrapper for existing LLM summarization functionality"""

    async def execute(self, document: DocumentMessage, parameters: Dict[str, Any] = None):
        # Delegate to existing LLM service
        if self.llm_service:
            return await self.llm_service.summarize(
                text=document.content.text,
                **parameters
            )
```

**Tools to Create**:
- `SummarizeTool` - Wraps `llm_service.summarize()`
- `ExtractEntitesTool` - Wraps `llm_service.extract_entities()`
- `ClassifyContentTool` - Wraps `llm_service.classify_content()`
- `GenerateTagsTool` - Wraps `llm_service.generate_tags()`

**Benefits**:
- Zero disruption to existing functionality
- Immediate availability in new tools API
- Allows gradual client migration

#### 1.2 Update Service Factory

Register document tools in the service startup process:

```python
# In application startup
from ...services.document_tools import initialize_document_tools

async def startup():
    # Initialize document tools system
    tool_init_result = initialize_document_tools()
    logger.info(f"Initialized {tool_init_result['registered_tools']} document tools")
```

### Phase 2: API Compatibility Layer (Week 2)

**Objective**: Maintain existing API endpoints while routing to new tools system

#### 2.1 Update Process Router

Modify existing process endpoints to use the new tools system internally:

```python
# backend/src/api/routers/process.py

@router.post("/summarize")
async def summarize_document_legacy(request: SummarizeRequest):
    """Legacy endpoint - now routes to document tools system"""

    # Get document
    document = await document_service.get_document(request.document_id)

    # Execute via tools system
    tool = DocumentToolRegistry.create(DocumentToolType.SUMMARIZE, ...)
    result = await tool.execute(document, request.parameters)

    # Return in legacy format
    return {"summary": result["summary"]}
```

#### 2.2 Deprecation Headers

Add deprecation headers to legacy endpoints:

```python
@router.post("/summarize", deprecated=True)
async def summarize_document_legacy(...):
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "2024-06-01"
    response.headers["Link"] = "</api/tools/execute>; rel=\"successor-version\""
```

### Phase 3: Enhanced Tool Implementations (Week 3-4)

**Objective**: Replace wrapper implementations with enhanced native tools

#### 3.1 Enhanced Summarization Tool

Replace wrapper with full implementation:

```python
@register_document_tool(DocumentToolType.SUMMARIZE)
class EnhancedSummarizeTool(BaseDocumentTool):
    """Enhanced summarization with multiple strategies"""

    def get_metadata(self) -> DocumentToolMetadata:
        return DocumentToolMetadata(
            # Enhanced capabilities
            capabilities=[
                DocumentToolCapability.TEXT_ANALYSIS,
                DocumentToolCapability.TEXT_GENERATION,
                DocumentToolCapability.CLASSIFICATION
            ],
            input_schema={
                "strategy": {
                    "type": "str",
                    "enum": ["extractive", "abstractive", "hybrid"],
                    "default": "hybrid"
                },
                "length": {
                    "type": "str",
                    "enum": ["short", "medium", "long"],
                    "default": "medium"
                }
                # ... enhanced parameters
            }
        )

    async def execute(self, document: DocumentMessage, parameters: Dict[str, Any] = None):
        # Enhanced implementation with multiple strategies
        strategy = parameters.get("strategy", "hybrid")

        if strategy == "extractive":
            return await self._extractive_summarization(document, parameters)
        elif strategy == "abstractive":
            return await self._abstractive_summarization(document, parameters)
        else:
            return await self._hybrid_summarization(document, parameters)
```

#### 3.2 Create Advanced Tools

Implement new tools that weren't possible with the hardcoded approach:

- **Multi-document Analysis Tools**
- **Workflow Tools** (combining multiple operations)
- **Format-specific Tools** (JSON schema validation, Excel analysis)
- **Collaborative Tools** (requiring multiple services)

### Phase 4: Client Migration (Week 5-6)

**Objective**: Migrate clients from legacy endpoints to new tools API

#### 4.1 Frontend Migration

Update frontend to use new tools endpoints:

```typescript
// Old approach
const summary = await api.post('/api/process/summarize', { document_id, ... });

// New approach
const recommendations = await api.post('/api/tools/recommendations', { document_id });
const result = await api.post('/api/tools/execute', {
    document_id,
    tool_type: 'summarize',
    parameters: { ... }
});
```

#### 4.2 Integration Migration

Provide migration guides for external integrations:

```bash
# Migration script example
./scripts/migrate-api-calls.sh --from=process --to=tools --config=migration.json
```

### Phase 5: Legacy Removal (Week 7)

**Objective**: Remove deprecated endpoints and clean up code

#### 5.1 Remove Legacy Endpoints

After sunset period, remove deprecated endpoints:

```python
# Remove from process.py:
# - /summarize
# - /extract-entities
# - /classify

# Remove from documents.py:
# - /{id}/validate (basic version)
```

#### 5.2 Remove Hardcoded Methods

Remove hardcoded methods from services:

```python
# Remove from LLMService:
# - summarize()
# - extract_entities()
# - classify_content()
```

## Implementation Details

### Service Dependencies

Update service creation to inject dependencies for tools:

```python
# In ServiceFactory
@classmethod
def create_document_tool(cls, tool_type: DocumentToolType) -> BaseDocumentTool:
    return DocumentToolRegistry.create(
        tool_type=tool_type,
        document_service=cls.create(ServiceType.DOCUMENT),
        llm_service=cls.create(ServiceType.LLM),
        vector_search_service=cls.create(ServiceType.VECTOR_SEARCH)
    )
```

### Configuration Migration

Move tool-specific configuration to tools system:

```python
# Old configuration in settings
llm:
  summarization:
    max_length: 500
    temperature: 0.7

# New configuration
document_tools:
  summarize:
    default_parameters:
      max_length: 500
      temperature: 0.7
```

### Testing Migration

Migrate tests to use tools system:

```python
# Old test
async def test_summarize():
    llm_service = ServiceFactory.create(ServiceType.LLM)
    result = await llm_service.summarize(text="...")

# New test
async def test_summarize_tool():
    tool = DocumentToolRegistry.create(DocumentToolType.SUMMARIZE, ...)
    result = await tool.execute(document, {"max_length": 100})
```

## Risk Mitigation

### Backward Compatibility

1. **API Versioning**: Use API versioning to maintain compatibility
   ```
   /api/v1/process/summarize  # Legacy
   /api/v2/tools/execute      # New
   ```

2. **Feature Flags**: Use feature flags to control rollout
   ```python
   if settings.features.new_tools_system:
       return await execute_via_tools(...)
   else:
       return await legacy_execute(...)
   ```

3. **Gradual Rollout**: Roll out tool-by-tool rather than all at once

### Monitoring and Rollback

1. **Usage Metrics**: Track usage of old vs new endpoints
2. **Error Monitoring**: Monitor error rates during migration
3. **Performance Monitoring**: Ensure new system performs as well as old
4. **Rollback Plan**: Ability to quickly revert to legacy system

## Success Metrics

- **API Coverage**: 100% of legacy functionality available via tools
- **Performance**: New system performs within 10% of legacy system
- **Client Adoption**: 90% of clients migrated within 8 weeks
- **Error Rate**: Error rate remains below 1% during migration
- **Tool Discovery**: 95% of appropriate tools recommended for documents

## Timeline Summary

| Week | Phase | Key Deliverables |
|------|-------|------------------|
| 1 | Wrapper Tools | All legacy functionality wrapped as tools |
| 2 | API Compatibility | Legacy endpoints route to tools internally |
| 3-4 | Enhanced Tools | Native implementations with enhanced features |
| 5-6 | Client Migration | Frontend and integrations migrated |
| 7 | Legacy Removal | Deprecated code removed |

## Post-Migration Benefits

1. **Dynamic Tool Discovery**: Clients can discover new tools automatically
2. **Enhanced Capabilities**: Tools provide richer metadata and capabilities
3. **Better Testing**: Tools are independently testable
4. **Easier Extensions**: New tools can be added without API changes
5. **Better Documentation**: Tools are self-documenting via metadata
6. **Recommendation System**: Intelligent tool suggestions for documents
7. **Batch Processing**: Tools support batch operations
8. **Service Isolation**: Tools encapsulate dependencies properly

## Rollback Plan

If issues arise during migration:

1. **Immediate**: Use feature flags to route to legacy system
2. **Short-term**: Revert API changes and disable tools router
3. **Analysis**: Identify and fix issues in tools system
4. **Re-migration**: Address issues and restart migration process

## Support and Documentation

1. **Migration Guide**: Step-by-step guide for developers
2. **API Documentation**: Updated OpenAPI specs
3. **Example Code**: Code samples for common migration patterns
4. **Support Channel**: Dedicated channel for migration questions
5. **FAQ**: Common questions and solutions