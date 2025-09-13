# Claude Code Guidelines for Mavn Bench Project

## Project Overview
**Mavn Bench** is a generic document processing platform with MCP tool integration, strict service and factory patterns, and full OpenTelemetry observability. This document contains ALL guidelines for Claude Code to implement the server-side components.

## Critical Project Information
- **Location**: `/Users/petermager/Downloads/code/mavn_bench`
- **GitHub**: https://github.com/petmar2017/mavn_bench
- **Python Version**: 3.13+ (MUST use venv)
- **Current Phase**: Phase 2 (Storage Layer) - Phase 1 COMPLETED ✅

## Development Methodology

### Core Principles
1. **Bottom-up Development**: Build each layer completely before moving up
2. **Test-Driven Development**: Write tests first, achieve 80%+ coverage
3. **NO MOCK Functions**: Only real implementations in tests
4. **Async Everything**: All I/O operations must be async
5. **Type Hints Required**: Every function must have type hints
6. **Factory Pattern**: All services created through factories
7. **Service Pattern**: All business logic in services
8. **Continuous Documentation**: Update docs with every change

### Environment Setup
```bash
# ALWAYS activate venv first
cd /Users/petermager/Downloads/code/mavn_bench/backend
source venv/bin/activate
python --version  # Must be 3.13+
```

## Architecture Patterns

### 1. Service Factory Pattern
```python
# ALWAYS create services through factory
from src.services.service_factory import ServiceFactory, ServiceType

# Register service
ServiceFactory.register(ServiceType.PDF, PDFService)

# Create service
pdf_service = ServiceFactory.create(ServiceType.PDF)
```

### 2. Storage Adapter Pattern
```python
# ALWAYS use storage through adapter
from src.storage.storage_factory import StorageFactory, StorageType

storage = StorageFactory.create(
    StorageType.FILESYSTEM,
    base_path="/document_store"
)
```

### 3. Base Service Pattern
```python
# ALL services MUST inherit from BaseService
class PDFService(BaseService):
    def __init__(self):
        super().__init__("PDFService")
    
    async def health_check(self) -> Dict[str, Any]:
        """Required for all services"""
        return {"service": "PDFService", "status": "healthy"}
```

## Implementation Phases

### Current Status
- ✅ **Phase 1**: Core Infrastructure (COMPLETED)
  - Configuration, Logging, Telemetry, Base Models, GitHub repo

### Next Implementation Order

#### Phase 2: Storage Layer (CURRENT)
```bash
# Files to create/complete
backend/src/storage/storage_factory.py
backend/src/storage/filesystem_storage.py  # Partially done
backend/src/storage/redis_storage.py
backend/tests/unit/test_storage/  # All tests
```

#### Phase 3: Service Layer
```bash
# Order of implementation
1. backend/src/services/service_factory.py
2. backend/src/services/document_service.py
3. backend/src/services/pdf_service.py
4. backend/src/services/transcription_service.py
5. backend/src/services/web_scraping_service.py
6. backend/src/services/llm_service.py
7. Search services (vector, graph, fulltext)
8. MCP services (registry, proxy)
```

#### Phase 4: API Layer
```bash
backend/src/api/main.py  # Partially done
backend/src/api/routers/documents.py
backend/src/api/routers/tools.py
backend/src/api/routers/search.py
backend/src/api/routers/process.py
backend/src/api/middleware/  # All middleware
```

## Code Standards

### Async/Await Requirements
```python
# ❌ NEVER - Blocking I/O
def read_file(path):
    with open(path) as f:
        return f.read()

# ✅ ALWAYS - Non-blocking I/O
async def read_file(path):
    async with aiofiles.open(path) as f:
        return await f.read()
```

### CPU-Intensive Tasks
```python
# ✅ CORRECT - Use thread pool for CPU tasks
async def process_pdf(file_path: str) -> str:
    return await asyncio.to_thread(self._sync_process_pdf, file_path)

def _sync_process_pdf(self, file_path: str) -> str:
    """Synchronous CPU-intensive processing"""
    doc = fitz.open(file_path)
    # Process...
    doc.close()
    return result
```

### Error Handling
```python
# ✅ ALWAYS include detailed error handling
async def process_document(self, doc_id: str) -> DocumentMessage:
    with self.traced_operation("process_document", doc_id=doc_id):
        try:
            document = await self.storage.load(doc_id)
            if not document:
                raise DocumentNotFoundError(f"Document {doc_id} not found")
            
            result = await self._process(document)
            self.logger.info(f"Processed document: {doc_id}")
            return result
            
        except DocumentNotFoundError:
            self.logger.error(f"Document not found: {doc_id}")
            raise
        except Exception as e:
            self.logger.error(f"Processing failed for {doc_id}: {str(e)}")
            raise ProcessingError(f"Failed to process {doc_id}") from e
```

### Type Hints
```python
# ✅ REQUIRED - Full type hints
from typing import Optional, List, Dict, Any

async def search_documents(
    query: str,
    limit: int = 10,
    offset: int = 0,
    filters: Optional[Dict[str, Any]] = None
) -> List[DocumentMessage]:
    """All parameters and returns must be typed"""
    pass
```

## Testing Requirements

### Test Structure
```
backend/tests/
├── unit/              # Unit tests for each module
│   ├── test_services/
│   ├── test_storage/
│   └── test_models/
├── integration/       # API integration tests
└── fixtures/         # Test data (NO MOCKS!)
```

### Testing Rules
1. **NO Mock Objects** - Use real implementations
2. **80% Coverage Minimum** - Check after each component
3. **Test Real Scenarios** - Use actual files, real databases
4. **Async Tests** - Use pytest-asyncio

### Test Example
```python
# ✅ CORRECT - Real implementation
@pytest.mark.asyncio
async def test_pdf_to_markdown(tmp_path):
    # Create real PDF file
    pdf_path = tmp_path / "test.pdf"
    create_actual_pdf(pdf_path)  # Real PDF creation
    
    # Test with real service
    service = ServiceFactory.create(ServiceType.PDF)
    result = await service.pdf_to_markdown(str(pdf_path))
    
    assert "## Page 1" in result
    assert len(result) > 0

# ❌ WRONG - Never use mocks
def test_with_mock():
    mock_service = Mock()  # NEVER DO THIS
    mock_service.process.return_value = "fake"
```

### Running Tests
```bash
# After implementing each component
cd backend
./venv/bin/pytest tests/unit/test_storage/ -v --cov=src/storage

# Check coverage
./venv/bin/pytest --cov=src --cov-report=html --cov-report=term-missing

# Coverage must be >= 80%
```

## OpenTelemetry Integration

### Every Service Must Have Tracing
```python
class PDFService(BaseService):
    async def pdf_to_markdown(self, file_path: str) -> str:
        # REQUIRED: Wrap all operations in tracing
        with self.traced_operation("pdf_to_markdown", file_path=file_path):
            try:
                result = await self._process(file_path)
                self.logger.info(f"Converted PDF: {file_path}")
                return result
            except Exception as e:
                self.logger.error(f"Failed: {str(e)}")
                raise
```

## Document Model Structure

### Core Document Message
```python
class DocumentMessage(BaseModel):
    """Core message passed between ALL components"""
    metadata: DocumentMetadata
    content: DocumentContent
    action: Optional[DocumentAction] = None
    tools: List[str] = Field(default_factory=list)
    history: List[DocumentVersion] = Field(default_factory=list)
    audit_log: List[AuditLogEntry] = Field(default_factory=list)
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
```

### Document Types
```python
class DocumentType(str, Enum):
    PDF = "pdf"
    WORD = "word"
    EXCEL = "excel"
    JSON = "json"
    XML = "xml"
    PODCAST = "podcast"
    YOUTUBE = "youtube"
    WEBPAGE = "webpage"
    MARKDOWN = "markdown"
    CSV = "csv"
```

## Service Implementation Order

### 1. Storage Services (Phase 2) - CURRENT
1. Complete `FilesystemStorage` (started)
2. Implement `RedisStorage`
3. Create `StorageFactory`
4. Write comprehensive tests
5. Achieve 80%+ coverage

### 2. Core Services (Phase 3.1)
1. `DocumentService` - CRUD operations
2. `PDFService` - PDF to markdown conversion
3. `TranscriptionService` - YouTube/Podcast transcription
4. `WebScrapingService` - Web page to markdown
5. `LLMService` - AI operations (summary, entities, Q&A)

### 3. Search Services (Phase 3.2)
1. `VectorSearchService` - Qdrant integration
2. `GraphSearchService` - Neo4j integration
3. `FulltextSearchService` - Elasticsearch integration

### 4. MCP Services (Phase 3.3)
1. `MCPRegistryService` - Tool registration/discovery
2. `MCPProxyService` - Tool execution proxy

## API Endpoints to Implement

### Document Endpoints
```python
POST   /api/documents              # Create document
GET    /api/documents              # List documents
GET    /api/documents/{id}         # Get document
PUT    /api/documents/{id}         # Update document
DELETE /api/documents/{id}         # Delete document
POST   /api/documents/upload       # Upload file
GET    /api/documents/{id}/versions # Get versions
```

### Processing Endpoints
```python
POST   /api/process/pdf-to-markdown  # Convert PDF
POST   /api/process/transcribe       # Transcribe media
POST   /api/process/scrape          # Scrape webpage
POST   /api/process/summarize       # Generate summary
POST   /api/process/extract-entities # Extract entities
```

### Tool Endpoints
```python
GET    /api/tools                   # List available tools
POST   /api/tools/register          # Register MCP tool
POST   /api/tools/{tool_id}/execute # Execute tool
GET    /api/tools/{document_type}   # Get tools for type
```

## Configuration Management

### Settings Structure
```python
# backend/src/core/config.py - ALREADY IMPLEMENTED
settings = get_settings()  # Cached singleton

# Access configuration
settings.storage.type  # "filesystem" or "redis"
settings.database.type  # "sqlite" or "postgresql"
settings.telemetry.enabled  # True/False
```

### Environment Variables
```bash
# .env file (create if needed)
STORAGE_TYPE=filesystem
DATABASE_TYPE=sqlite
TELEMETRY_ENABLED=true
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
```

## Git Workflow

### After Each Component
```bash
# 1. Format code
cd backend
./venv/bin/black src/ tests/
./venv/bin/isort src/ tests/

# 2. Run tests
./venv/bin/pytest tests/ -v --cov=src

# 3. Commit with detailed message
git add .
git commit -m "Implement [Component Name]

- Added [specific features]
- Implemented [specific methods]
- Achieved [X]% test coverage
- Follows factory/service patterns"

# 4. Push to GitHub
git push origin main
```

## Common Pitfalls to Avoid

### ❌ NEVER DO THESE:
1. Use synchronous I/O in async functions
2. Forget to close resources (always use context managers)
3. Skip error handling
4. Omit type hints
5. Use global state
6. Hardcode configuration values
7. Skip tests or use mocks
8. Block the event loop
9. Mix sync and async without proper handling
10. Ignore the venv

### ✅ ALWAYS DO THESE:
1. Use `async/await` for all I/O
2. Use `async with` for resource management
3. Handle all exceptions explicitly
4. Include type hints for everything
5. Use dependency injection
6. Use configuration from settings
7. Write real tests with 80%+ coverage
8. Use thread pool for CPU tasks
9. Follow factory and service patterns
10. Activate venv before any work

## Performance Requirements

### Target Metrics
- API Response Time: < 200ms (p95)
- Document Processing: < 30s for 10MB PDF
- Search Latency: < 100ms
- Concurrent Users: 100+
- Test Coverage: >= 80%
- No blocking operations in async code

## Debugging and Logging

### Use Structured Logging
```python
# ALWAYS use the centralized logger
self.logger.debug(f"Starting process for {doc_id}")
self.logger.info(f"Successfully processed {doc_id}")
self.logger.warning(f"Slow processing: {duration}s")
self.logger.error(f"Failed: {str(e)}", exc_info=True)
```

### Use Tracing for Performance
```python
# ALWAYS wrap operations in tracing
with self.traced_operation("operation_name", **attributes):
    # Your code here
    pass
```

## Makefile Commands

### Available Commands
```bash
make help              # Show all commands
make setup            # Initial setup
make dev-backend      # Start backend dev server
make test-backend     # Run backend tests
make test-all         # Run all tests
make format           # Format code
make clean            # Clean artifacts
```

## Quick Reference Checklist

Before implementing any component:
- [ ] Activated venv (`source venv/bin/activate`)
- [ ] Checked Python version (`python --version` >= 3.13)
- [ ] Read the relevant section in ARCHITECTURE.md
- [ ] Located template in SERVICE_IMPLEMENTATION_GUIDE.md

While implementing:
- [ ] Using async/await for all I/O
- [ ] Adding type hints to all functions
- [ ] Following factory/service patterns
- [ ] Including error handling
- [ ] Adding logging with trace context
- [ ] Writing docstrings

After implementing:
- [ ] Written tests (no mocks!)
- [ ] Achieved 80%+ coverage
- [ ] Formatted code (black/isort)
- [ ] Updated documentation
- [ ] Committed with detailed message
- [ ] Pushed to GitHub

## Project File References

### Documentation
- `docs/ARCHITECTURE.md` - Complete system design
- `docs/IMPLEMENTATION_PLAN.md` - Detailed phase plan
- `docs/SERVICE_IMPLEMENTATION_GUIDE.md` - Code templates
- `prompt.md` - General development guidelines
- `claude.md` - THIS FILE - Project-specific guidelines

### Current Implementation Status
- ✅ `backend/src/core/` - COMPLETED
- ✅ `backend/src/models/document.py` - COMPLETED
- ✅ `backend/src/services/base_service.py` - COMPLETED
- 🚧 `backend/src/storage/` - IN PROGRESS (Phase 2)
- ⏳ `backend/src/services/` - NEXT (Phase 3)
- ⏳ `backend/src/api/` - FUTURE (Phase 4)

## Final Reminders

1. **ALWAYS use venv** - Never install packages globally
2. **NO MOCKS in tests** - Real implementations only
3. **80% coverage minimum** - Test after each component
4. **Follow patterns exactly** - Use templates from guides
5. **Async everything** - No blocking operations
6. **Type hints required** - On all functions
7. **Factory pattern** - For all services/storage
8. **Trace everything** - OpenTelemetry on all operations
9. **Document changes** - Update docs as you go
10. **Test continuously** - Don't wait until the end

---
**Project**: Mavn Bench  
**Location**: `/Users/petermager/Downloads/code/mavn_bench`  
**GitHub**: https://github.com/petmar2017/mavn_bench  
**Current Phase**: Phase 2 - Storage Layer  
**Next Task**: Complete FilesystemStorage implementation and tests  
