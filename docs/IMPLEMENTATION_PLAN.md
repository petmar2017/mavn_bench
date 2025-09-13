# Mavn Bench - Detailed Implementation Plan

## Project Overview
Mavn Bench is a generic document processing platform with MCP tool integration, following strict service and factory patterns for Python 3.13+ compatibility.

## Development Principles

### Core Requirements
- **Python Version**: 3.13+ (use venv for isolation)
- **Design Patterns**: Strict Service and Factory patterns
- **Testing**: TDD with 80%+ coverage, NO mock functions
- **Observability**: Full OpenTelemetry integration
- **Architecture**: Event-driven, microservices-ready
- **Configuration**: Server-side driven

### Development Methodology
1. Bottom-up development approach
2. Complete each layer before moving up
3. Test after every component
4. Real implementations only (no mocks)
5. Continuous documentation

## Implementation Phases

## Phase 1: Core Infrastructure (COMPLETED ✅)
- [x] Project structure
- [x] Configuration management
- [x] Logging with OpenTelemetry
- [x] Base service class
- [x] Document models
- [x] GitHub repository

## Phase 2: Storage Layer (CURRENT 🚧)

### 2.1 Storage Factory Implementation
```python
# backend/src/storage/storage_factory.py
class StorageFactory:
    @staticmethod
    def create_storage(storage_type: str) -> StorageAdapter
```

**Files to create:**
- `backend/src/storage/storage_factory.py`
- `backend/src/storage/filesystem_storage.py`
- `backend/src/storage/redis_storage.py`
- `backend/tests/test_storage.py`

**Requirements:**
- Implement adapter pattern for storage
- Support filesystem and Redis backends
- Async/await for all I/O operations
- Version control for documents
- Atomic operations with rollback

### 2.2 Testing Storage Layer
```bash
cd backend
./venv/bin/pytest tests/test_storage.py -v --cov=src/storage
```

## Phase 3: Service Layer Implementation

### 3.1 Service Factory Pattern
```python
# backend/src/services/service_factory.py
class ServiceFactory:
    @staticmethod
    def create_service(service_type: ServiceType) -> BaseService
```

### 3.2 Document Processing Services

#### DocumentService
**Path**: `backend/src/services/document_service.py`
**Responsibilities:**
- CRUD operations
- Version management
- Access control
- Audit logging

#### PDFService
**Path**: `backend/src/services/pdf_service.py`
**Dependencies:**
- PyMuPDF for extraction
- pdf2image for preview
- OCR support (optional)
**Methods:**
- `async def pdf_to_markdown(file_path: str) -> str`
- `async def extract_metadata(file_path: str) -> Dict`
- `async def extract_tables(file_path: str) -> List[DataFrame]`

#### TranscriptionService
**Path**: `backend/src/services/transcription_service.py`
**Dependencies:**
- OpenAI Whisper API
- yt-dlp for download
- Audio processing libraries
**Methods:**
- `async def transcribe_youtube(url: str) -> DocumentMessage`
- `async def transcribe_podcast(url: str) -> DocumentMessage`
- `async def transcribe_audio_file(file_path: str) -> str`

#### WebScrapingService
**Path**: `backend/src/services/scraping_service.py`
**Dependencies:**
- BeautifulSoup4
- Playwright for JS sites
- html2text for markdown
**Methods:**
- `async def scrape_to_markdown(url: str) -> str`
- `async def extract_structured_data(url: str) -> Dict`

#### LLMService
**Path**: `backend/src/services/llm_service.py`
**Dependencies:**
- OpenAI API
- Anthropic API
- Rate limiting
- Retry logic
**Methods:**
- `async def generate_summary(text: str) -> str`
- `async def extract_entities(text: str) -> List[Entity]`
- `async def classify_document(text: str) -> DocumentType`
- `async def answer_question(context: str, question: str) -> str`

### 3.3 Search Services

#### VectorSearchService
**Path**: `backend/src/services/vector_search_service.py`
**Dependencies:**
- Qdrant client
- Embedding generation
- Similarity metrics

#### GraphSearchService
**Path**: `backend/src/services/graph_search_service.py`
**Dependencies:**
- Neo4j driver
- Graph algorithms
- Relationship mapping

#### FullTextSearchService
**Path**: `backend/src/services/fulltext_search_service.py`
**Dependencies:**
- Elasticsearch client
- Query DSL
- Aggregations

### 3.4 MCP Integration Services

#### MCPRegistryService
**Path**: `backend/src/services/mcp_registry_service.py`
**Responsibilities:**
- Tool registration
- Tool discovery
- Capability mapping

#### MCPProxyService
**Path**: `backend/src/services/mcp_proxy_service.py`
**Responsibilities:**
- Request forwarding
- Response transformation
- Error handling

## Phase 4: API Layer Implementation

### 4.1 FastAPI Application Structure
```
backend/src/api/
├── main.py                 # Application entry point
├── dependencies.py         # Dependency injection
├── middleware/
│   ├── auth.py
│   ├── telemetry.py
│   └── error_handler.py
├── routers/
│   ├── documents.py       # Document CRUD endpoints
│   ├── tools.py          # MCP tool endpoints
│   ├── search.py         # Search endpoints
│   ├── process.py        # Processing endpoints
│   └── auth.py           # Authentication
└── websockets/
    └── events.py          # WebSocket for real-time events
```

### 4.2 API Endpoints

#### Document Endpoints
- `POST /api/documents` - Create document
- `GET /api/documents/{id}` - Get document
- `PUT /api/documents/{id}` - Update document
- `DELETE /api/documents/{id}` - Delete document
- `GET /api/documents` - List documents
- `POST /api/documents/upload` - Upload file
- `GET /api/documents/{id}/versions` - Get versions
- `POST /api/documents/{id}/revert/{version}` - Revert to version

#### Processing Endpoints
- `POST /api/process/pdf-to-markdown` - Convert PDF
- `POST /api/process/transcribe` - Transcribe media
- `POST /api/process/scrape` - Scrape webpage
- `POST /api/process/summarize` - Generate summary
- `POST /api/process/extract-entities` - Extract entities

#### Tool Endpoints
- `GET /api/tools` - List available tools
- `POST /api/tools/register` - Register MCP tool
- `POST /api/tools/{tool_id}/execute` - Execute tool
- `GET /api/tools/{document_type}` - Get tools for type

#### Search Endpoints
- `POST /api/search/vector` - Vector search
- `POST /api/search/graph` - Graph search
- `POST /api/search/fulltext` - Full-text search
- `POST /api/search/hybrid` - Hybrid search

### 4.3 WebSocket Events
```python
# Event types
class DocumentEvent:
    CREATED = "document.created"
    UPDATED = "document.updated"
    DELETED = "document.deleted"
    PROCESSING = "document.processing"
    PROCESSED = "document.processed"
    ERROR = "document.error"
```

## Phase 5: Database Layer

### 5.1 Database Factory
```python
# backend/src/core/database_factory.py
class DatabaseFactory:
    @staticmethod
    def create_database(db_type: str) -> DatabaseAdapter
```

### 5.2 Models (SQLAlchemy)
```python
# backend/src/models/db_models.py
- User
- ApiKey
- Document
- DocumentVersion
- AuditLog
- Tool
- Permission
```

### 5.3 Migrations
```bash
# Initialize Alembic
cd backend
alembic init alembic
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

## Phase 6: Testing Implementation

### 6.1 Test Structure
```
backend/tests/
├── unit/
│   ├── test_services/
│   ├── test_storage/
│   └── test_models/
├── integration/
│   ├── test_api/
│   └── test_database/
├── e2e/
│   └── test_workflows/
├── fixtures/
│   ├── documents/
│   └── data.py
└── conftest.py
```

### 6.2 Test Coverage Requirements
- Unit tests: 80%+ coverage
- Integration tests: All API endpoints
- E2E tests: Critical workflows
- Performance tests: Load testing

### 6.3 Test Commands
```bash
# Run all tests
make test-all

# Run with coverage
./venv/bin/pytest --cov=src --cov-report=html

# Run specific test file
./venv/bin/pytest tests/unit/test_services/test_pdf_service.py -v

# Run only smoke tests
./venv/bin/pytest -m smoke
```

## Phase 7: Monitoring & Observability

### 7.1 OpenTelemetry Setup
- Traces: All service methods
- Metrics: Performance counters
- Logs: Structured with trace context
- Exporters: OTLP, Jaeger, Prometheus

### 7.2 Health Checks
```python
# backend/src/api/health.py
@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "checks": {
            "database": check_database(),
            "redis": check_redis(),
            "storage": check_storage()
        }
    }
```

### 7.3 Metrics Collection
- Request duration
- Error rates
- Document processing times
- Queue lengths
- Resource usage

## Phase 8: Security Implementation

### 8.1 Authentication
- API key validation
- JWT tokens for sessions
- Rate limiting per key
- IP allowlisting (optional)

### 8.2 Authorization
- Role-based access control (RBAC)
- Document-level permissions
- Group management
- Audit logging

### 8.3 Security Headers
- CORS configuration
- CSP headers
- Rate limiting
- Request validation

## Phase 9: Background Tasks

### 9.1 Task Queue Setup
```python
# backend/src/tasks/celery_app.py
from celery import Celery

celery_app = Celery(
    'mavn_bench',
    broker='redis://localhost:6379',
    backend='redis://localhost:6379'
)
```

### 9.2 Background Tasks
- Document processing
- Transcription jobs
- Embedding generation
- Search indexing
- Cleanup tasks

## Phase 10: Deployment Preparation

### 10.1 Docker Configuration
```dockerfile
# backend/Dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 10.2 Environment Configuration
```yaml
# config/settings.yaml
development:
  debug: true
  database: sqlite
  
staging:
  debug: false
  database: postgresql
  
production:
  debug: false
  database: postgresql
  redis: cluster
```

### 10.3 CI/CD Pipeline
```yaml
# .github/workflows/backend.yml
- Run tests
- Check coverage
- Build Docker image
- Deploy to staging
- Run E2E tests
- Deploy to production
```

## Completion Checklist

### Phase 2: Storage Layer
- [ ] Create storage factory
- [ ] Implement filesystem storage
- [ ] Implement Redis storage
- [ ] Add version control
- [ ] Write unit tests
- [ ] Test with 80%+ coverage

### Phase 3: Service Layer
- [ ] Create service factory
- [ ] Implement DocumentService
- [ ] Implement PDFService
- [ ] Implement TranscriptionService
- [ ] Implement WebScrapingService
- [ ] Implement LLMService
- [ ] Implement search services
- [ ] Implement MCP services
- [ ] Write comprehensive tests

### Phase 4: API Layer
- [ ] Setup FastAPI application
- [ ] Create all routers
- [ ] Implement middleware
- [ ] Add WebSocket support
- [ ] Create OpenAPI documentation
- [ ] Test all endpoints

### Phase 5: Database Layer
- [ ] Setup database factory
- [ ] Create SQLAlchemy models
- [ ] Setup Alembic migrations
- [ ] Implement repositories
- [ ] Add connection pooling

### Phase 6: Testing
- [ ] Setup test structure
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Write E2E tests
- [ ] Achieve 80%+ coverage

### Phase 7: Monitoring
- [ ] Configure OpenTelemetry
- [ ] Add health checks
- [ ] Setup metrics collection
- [ ] Configure alerting

### Phase 8: Security
- [ ] Implement authentication
- [ ] Add authorization
- [ ] Configure security headers
- [ ] Add rate limiting

### Phase 9: Background Tasks
- [ ] Setup Celery
- [ ] Implement task queue
- [ ] Add task monitoring
- [ ] Configure retries

### Phase 10: Deployment
- [ ] Create Dockerfile
- [ ] Setup Docker Compose
- [ ] Configure CI/CD
- [ ] Create deployment scripts
- [ ] Document deployment process

## Success Criteria
1. All tests passing with 80%+ coverage
2. All API endpoints documented
3. Full OpenTelemetry tracing
4. Sub-200ms response times
5. Handles 100+ concurrent users
6. Zero mock implementations
7. Complete audit trail
8. Production-ready security

## Timeline Estimate
- Phase 2: 2 days
- Phase 3: 4 days
- Phase 4: 3 days
- Phase 5: 2 days
- Phase 6: 2 days
- Phase 7-10: 3 days
- **Total: ~16 days**

## Notes for Claude Code
1. Always use async/await for I/O operations
2. Follow service factory pattern strictly
3. Test each component before moving forward
4. Use type hints everywhere
5. Document all public methods
6. Handle errors gracefully
7. Log with trace context
8. Never use mock functions in tests

---
*Last Updated: September 13, 2025*
*Version: 1.0.0*
