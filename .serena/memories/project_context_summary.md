# Mavn Bench Project Context

## Overview
- **Project**: Generic document processing platform with MCP tool integration
- **Location**: `/Users/petermager/Downloads/code/mavn_bench`
- **GitHub**: https://github.com/petmar2017/mavn_bench
- **Status**: Active Development - Phase 5 (Frontend Implementation)
- **Phases 1-4**: ✅ COMPLETED (Infrastructure, Storage, Services, API)

## Technology Stack

### Backend (Python 3.13+)
- **Framework**: FastAPI with async/await throughout
- **Database**: SQLite (dev), PostgreSQL (production)
- **Storage**: Filesystem/Redis adapters with factory pattern
- **Search**: Qdrant (vector), Neo4j (graph), Elasticsearch (full-text)
- **Observability**: OpenTelemetry with distributed tracing
- **Testing**: Pytest with 80%+ coverage (398 tests collected)
- **Patterns**: Service factory, storage adapter, base service inheritance

### Frontend (Node 18+, React 19)
- **Framework**: React 19 with TypeScript
- **Styling**: Plain CSS with CSS Modules (NO UI libraries like Chakra UI)
- **Build**: Vite
- **Testing**: Vitest with React Testing Library
- **HTTP**: Axios for API calls
- **WebSocket**: Socket.IO Client
- **Data Grid**: AG-Grid React
- **Icons**: Lucide React
- **State**: React hooks (useState, useEffect)

## Architecture Highlights

### Core Patterns
1. **Service Factory**: All services created through `ServiceFactory.create(ServiceType.X)`
2. **Storage Adapter**: Flexible storage via `StorageFactory.create(StorageType.X)`
3. **Base Service**: All services inherit from `BaseService` with tracing
4. **Document Message**: Core `DocumentMessage` model passed between ALL components
5. **Event-Driven**: Reactive architecture with document message passing
6. **Lazy Loading**: Frontend uses content caching service with 5-min TTL

### Document Types Supported
- PDF, Word, Excel, JSON, XML, CSV
- YouTube, Podcast (transcription)
- Webpage (web scraping to markdown)
- Markdown, Text

## Project Structure

### Backend (`/backend/`)
```
src/
├── core/              # Config, logging, telemetry ✅
├── models/            # Pydantic models (DocumentMessage) ✅
├── storage/           # Storage adapters (filesystem, redis) ✅
├── services/          # Business logic services ✅
│   ├── llm/          # LLM tools (summarization, entities, etc.) ✅
│   └── document_tools/ # Document-specific tools ✅
├── api/              # FastAPI routes and middleware ✅
│   ├── routers/      # Documents, tools, search, process ✅
│   └── middleware/   # Auth, telemetry, error handling ✅
└── tools/            # Generic tool system with adapters ✅
```

### Frontend (`/frontend/`)
```
src/
├── components/
│   ├── Bench/         # Document viewing/editing workspace
│   ├── ToolsMenu/     # Tool execution interface
│   └── (others)       # Upload, List, Search, etc.
├── services/          # API, WebSocket, content caching
├── types/             # TypeScript type definitions
├── utils/             # Helper functions
└── styles/            # Global CSS + CSS modules
```

## Key Configuration

### Environment Variables (`.env`)
- Storage: `STORAGE_TYPE=filesystem` or `redis`
- Database: `DATABASE_TYPE=sqlite` or `postgresql`
- Telemetry: `TELEMETRY_ENABLED=true`
- LLM: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`
- API: `API_HOST=0.0.0.0`, `API_PORT=8000`

### Development Commands
- **Setup**: `make setup` (backend venv + frontend deps)
- **Dev**: `make dev-all-logs` (both services with logs)
- **Test**: `make test-backend`, `make test-frontend`
- **Stop**: `make stop-all` (kills all services)
- **Restart**: `make restart-clean` (clean restart)

## Testing Strategy
- **Backend**: 398 tests, 80%+ coverage, NO MOCKS (real implementations)
- **Frontend**: Vitest with React Testing Library
- **Integration**: API endpoint tests, WebSocket tests
- **Coverage**: Pytest with `--cov=src --cov-report=term-missing`

## Development Workflow
1. ALWAYS activate venv: `cd backend && source venv/bin/activate`
2. Check Python version: `python --version` (must be 3.13+)
3. Use async/await for ALL I/O operations
4. Follow factory/service patterns exactly
5. Include type hints on all functions
6. Write tests first (TDD), achieve 80%+ coverage
7. Format with black/isort before commit
8. Update docs with every change

## Critical Rules
- ❌ NO Mock functions in tests - use real implementations
- ❌ NO blocking I/O in async code - use `asyncio.to_thread()` for CPU tasks
- ❌ NO UI component libraries (Chakra, Material-UI) - use plain React + CSS
- ✅ ALWAYS use venv for backend work
- ✅ ALWAYS add type hints to functions
- ✅ ALWAYS use factory patterns for services/storage
- ✅ ALWAYS wrap operations in `traced_operation()` for observability

## Current Phase: Phase 5 - Frontend Implementation
Focus on building React components with:
- Split-panel UI (400px left sidebar + flexible workspace)
- Document viewers for all types (Markdown, Excel, JSON, PDF, etc.)
- Lazy-loaded content with caching
- WebSocket real-time updates
- Native React components with CSS Modules
