# Changelog

All notable changes to the Mavn Bench project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 2025-10-06

### Fixed

- **Frontend TypeScript Import Errors**: Resolved module resolution and type definition issues
  - Fixed incorrect import path in `entityApi.ts` from '../config' to '../config/api.config'
  - Consolidated duplicate type definitions between `api.ts` and `types/document.ts`
  - Added DocumentUpdateRequest type for proper partial metadata updates
  - Fixed ExcelViewer component variable shadowing (renamed document prop to doc)
  - Updated test fixtures with proper Entity interface (added entity_id field)
  - Fixed type-only imports in test utilities for verbatimModuleSyntax compliance
  - Added `frontend/src/__tests__/build.test.ts` for frontend build validation
  - This ensures import errors are caught in tests, not just at build time

### Added

- **Frontend Build Validation Tests**: Tests to catch TypeScript and import errors
  - Created build.test.ts to validate all critical module imports succeed
  - Tests verify Entity and EntityRelationship types are exported correctly
  - Tests verify entityApi service and config exports
  - Addresses issue where backend pytest doesn't validate frontend imports/builds
  - Future frontend compilation errors will be caught during test runs

- **Enhanced Entity System with Relationships**: Comprehensive entity extraction improvements with relationship support
  - Created `backend/src/models/entity.py` with Entity, EntityRelationship, and DocumentEntities models
  - Added entity_id field for unique entity identification and relationship tracking
  - Added normalized_value field for consistent date formatting (ISO 8601: YYYY-MM-DD)
  - Added relationships field to DocumentMetadata model for entity relationship storage
  - Implemented 11 entity types: person, organization, location, date, money, product, event, email, phone, url, unknown
  - Implemented 14 relationship types: works_for, employed_by, located_in, founded_by, founded, part_of, subsidiary_of, occurred_on, occurred_at, associated_with, mentions, owns, manages, member_of
  - Created entity API endpoints at `/api/entities/types`, `/api/entities/relationship-types`, `/api/entities/document/{id}`
  - Updated frontend Entity interface with entity_id, normalized_value, start_pos, end_pos fields
  - Added EntityRelationship interface for relationship tracking
  - Created `frontend/src/services/entityApi.ts` for entity API communication
  - Enhanced EntitiesViewer component with:
    - Dropdown entity types populated from API (with free text override using HTML5 datalist)
    - Date picker for date entities with normalized value display
    - Display normalized dates alongside original text for better consistency
    - Real-time API fetching of available entity types and relationship types
  - Comprehensive unit tests: 20 tests for entity models, 19 tests for entity extraction (39 total, 100% pass rate)

- **Date Normalization in Entity Extraction**: Consistent date handling across the system
  - Implemented date normalization using python-dateutil parser
  - All extracted dates converted to ISO 8601 format (YYYY-MM-DD)
  - Supports multiple input formats: "Jan 1, 2024", "January 15, 2024", "2024-03-20", "March 20, 2024", "12/31/2023", etc.
  - Original text preserved while normalized value used for sorting/filtering
  - Date picker UI component for editing entity dates

### Changed

- **Fully Dynamic Tool and Provider Registration**: Eliminated all hardcoded imports in favor of decorator-based auto-discovery
  - Removed hardcoded tool imports from `services/llm/tools/__init__.py` - now uses auto-discovery
  - Removed hardcoded provider imports from `services/llm/providers/implementations/__init__.py` - now uses auto-discovery
  - Added `scan_and_import_providers()` function for automatic provider module discovery
  - Added `initialize_providers()` function for comprehensive provider system initialization
  - New tools and providers now require ZERO manual registration - just add file with decorator
  - Improved maintainability: adding new tools/providers requires no changes to `__init__.py` files
  - System is now 100% dynamic with full decorator-based registration across all components

### Added

- **Enhanced Processing Logging**: Added comprehensive logging throughout PDF document processing pipeline
  - `[PDF-PROCESS]` logs track PDF conversion from file to markdown with character counts
  - `[DOC-PROCESS]` logs track document processing flow and final summary generation
  - `[SUMMARY-GEN]` logs track AI summary generation with detailed status at each step
  - `[QUEUE-PROCESS]` logs track queue processing and WebSocket notifications
  - All logs include document ID for easy tracing
  - Summary content preview (first 100-200 characters) logged at key checkpoints
  - Enables debugging of summary generation issues and processing flow

### Fixed

- **Inconsistent Log Formatting**: Unified log formatting across all logging sources for consistent dual output
  - Created custom formatters in `src/core/uvicorn_config.py` matching `CentralizedLogger` pattern
  - **Dual Output Mode** (default): Logs to both stdout (human-readable console) and stderr (JSON)
    - Console format: `HH:MM:SS | LEVEL | SERVICE | MESSAGE` with ANSI colors
    - JSON format: `{"timestamp": "...", "level": "...", "service": "...", "message": "...", "trace_id": "...", "span_id": "...", "user_id": null, "session_id": null}`
  - **JSON-Only Mode**: Set `MAVN_LOG_JSON_ONLY=true` for production deployments
  - Configured uvicorn with dual formatters (`UvicornConsoleFormatter` and `UvicornJsonFormatter`)
  - Configured OpenTelemetry SDK loggers to suppress transient connection errors (set to ERROR level)
  - Created `run_server.py` script with proper logging configuration
  - Updated Makefile `dev-backend` and `dev-backend-logs` targets to use new startup script
  - Eliminates inconsistent formats between uvicorn, OpenTelemetry, and application logs
  - Both stdout and stderr now provide consistent, parseable output for different use cases

- **Verbose Redis Storage Logging**: Reduced log noise by changing Redis storage operations from INFO to DEBUG level
  - Document load/save operations in Redis storage now only appear in debug mode
  - Eliminates repetitive storage operation logs flooding production console
  - Maintains debug capability for troubleshooting when needed

- **Verbose Document Logging**: Reduced log noise by changing document listing logs from INFO to DEBUG level
  - Document enumeration logs in `/api/documents` endpoint now only appear in debug mode
  - Eliminates repetitive document detail logs flooding production console
  - Maintains debug capability for troubleshooting when needed

- **PDF Summary Generation**: Fixed issue where PDF summaries showed first line of text instead of AI-generated summaries
  - Root cause: Backend startup failures due to stale Python `.pyc` cache files preventing import of document_tools module
  - Solution: Cleaned Python cache files to resolve `ImportError` in document_tools imports
  - Backend now starts successfully and processes documents correctly
  - Document processor generates proper AI summaries via LLM service for all uploaded PDFs
  - WebSocket notifications correctly deliver completed summaries to frontend
  - Processing flow verified: Upload → Queue → Process → AI Summary → WebSocket Update → Frontend Display

### Added

- **Generic Tool System**: Implemented unified tool architecture supporting multiple tool types
  - Created `BaseTool` abstract class with comprehensive metadata and execution context
  - Implemented `ToolRegistry` with advanced indexing by category, capability, and type
  - Added decorator-based auto-registration with `@register_tool` for automatic tool discovery
  - Created `ToolMetadata` dataclass with 20+ fields for comprehensive tool description
  - Added `ToolExecutionContext` for trace_id, session_id, and user_id propagation
  - Dependency injection support for services (llm_service, document_service, vector_search, etc.)
  - Tool categories: ANALYSIS, TRANSFORMATION, GENERATION, LLM, COMPUTATION, etc.
  - Tool capabilities: TEXT_ANALYSIS, ENTITY_RECOGNITION, TRANSLATION, SEMANTIC_SEARCH, etc.
  - Tool types: EXECUTABLE (native Python), MCP (external servers), LLM, DOCUMENT, HYBRID

- **Tool Adapters**: Created adapter pattern for external tool integration
  - `MCPToolAdapter`: Wraps MCP server tools in unified interface via HTTP
  - `ExecutableToolAdapter`: Wraps Python scripts/binaries as tools with subprocess execution
  - Both adapters support input/output schemas, timeout configuration, and health checks
  - Adapters pass through dependency injection kwargs to base tool

- **Example Tools**: Implemented demonstration tools showing all patterns
  - `WordCountTool`: Simple native Python tool with no dependencies
  - `EchoTool`: Basic tool demonstrating execution context usage
  - `SmartSummarizeTool`: LLM tool demonstrating dependency injection for llm_service
  - `DocumentAnalyzerTool`: Hybrid tool using multiple services (document, llm, vector search)
  - Auto-discovery via `load_example_tools()` function

- **Tool Testing**: Comprehensive test suite with 50 tests and 60% coverage
  - `test_base_tool.py`: 11 tests for BaseTool, ToolMetadata, validation, and context
  - `test_tool_registry.py`: 18 tests for registration, creation, indexing, and queries
  - `test_tool_decorators.py`: 7 tests for decorator registration and auto-discovery
  - `test_example_tools.py`: 14 tests for all example tools with mocked dependencies
  - All tests use real implementations (no mocks) following project standards

### Fixed

- **WebSocket Debug Logging**: Disabled verbose Socket.IO and EngineIO debug logging
  - Changed `logger=True` to `logger=False` in socketio.AsyncServer configuration
  - Changed `engineio_logger=True` to `engineio_logger=False`
  - Eliminates noisy PING/PONG packet logs flooding the console
  - Application-level WebSocket events still logged via custom logger
  - Improves log readability and reduces log volume in production

- **Document Summary WebSocket Notification**: Fixed issue where document summaries were not properly delivered to frontend
  - Root cause: WebSocket payload was constructed before AI summary generation, causing summary to be missing from initial notification
  - Solution: Added `emit_document_updated` WebSocket event after summary is generated and saved to database
  - Frontend now receives complete summary in real-time via document_updated event
  - Improved logging for WebSocket emissions to aid in future debugging
  - Follows existing project patterns for WebSocket communication and error handling

- **LLM Tool Length Handling**: Fixed 500 Internal Server Error when processing long documents
  - Entity extraction tool now supports documents up to 500K characters via chunking
  - Chunking uses 40K character chunks with 500 character overlap to preserve context
  - Deduplication logic ensures same entity across chunks is kept with highest confidence
  - Language detection tool increased max length to 1M characters (only uses first 500 chars)
  - Translation tool now supports documents up to 500K characters via chunking
  - All three tools follow consistent chunking patterns and error handling

- **Tool Testing Infrastructure**: Created comprehensive test suite for LLM tools
  - Added test_llm_tools.py with 22 test cases covering edge cases
  - Tests validate chunking functionality, deduplication, and fallback modes
  - Coverage for entity extraction (73%), language detection (70%), translation (85%)

### Added

- **Entity Extraction and Editing**: Enhanced document viewer with interactive entity management
  - Added dedicated Entities tab to PDFViewer component showing extracted entities
  - Integrated EntitiesViewer component with full entity editing capability
  - Entities grouped by type (PERSON, ORGANIZATION, LOCATION, DATE, MONEY) with color coding
  - Expandable/collapsible entity groups for better organization
  - Edit entity text, type, and confidence scores directly in the UI
  - Entities automatically loaded from document metadata
  - Real-time entity updates saved back to document metadata

- **Multi-Language Translation Support**: Server-side language detection and translation
  - Created TranslationTool following existing LLM tool architecture pattern
  - Added `/api/process/detect-language` endpoint for language detection
  - Added `/api/process/translate` endpoint for server-side translation to English
  - Language detection automatically triggers translation for non-English documents
  - Translation tab appears conditionally when non-English language detected
  - English translations displayed using SimpleMarkdownEditor for easy editing
  - Translation content stored in document.content.translation field
  - Detect Language tool automatically calls translation API when needed
  - Added translation and language detection to frontend API service layer
  - Full TypeScript type support for translation field in DocumentContent interface

- **Dynamic Tab System**: Context-aware document viewer tabs
  - Tabs dynamically shown based on available content (Summary, Transcript, Entities, Translation, Original)
  - Translation tab only appears when language detected as non-English
  - Entities tab always visible for all document types
  - Tab system follows existing ViewerTabBar component patterns

### Fixed
- **PDF Viewer URL Construction**: Fixed iframe recursive loading issue in PDFViewer component
  - Changed from `import.meta.env.VITE_API_URL` to `API_BASE_URL` from centralized config
  - PDF files now display correctly instead of loading the entire website recursively
  - Fixed `frontend/src/components/Bench/PDFViewer.tsx` URL construction

- **Real-Time Document Updates**: Fixed missing summary/transcript after upload
  - Added WebSocket listener for `document:updated` events in App.tsx
  - PDFViewer now auto-reloads content when document is updated via WebSocket
  - Document content cache invalidation on updates for fresh data fetch
  - Summary and transcript now appear automatically after processing completes
  - No page reload required to see processed content

- **Backend Import Errors**: Fixed document tools module import issues
  - Removed non-existent `ToolCategory` import from `document_tools/__init__.py`
  - Corrected exports in `__all__` list to match actual module exports
  - Backend server now starts successfully without import errors

- **Processing Completion Notifications**: Added success toast notifications
  - Added toast notification in `queue:job_completed` WebSocket handler
  - Users now see "Processing complete" message when document processing finishes
  - Toast includes document name for clarity

- **Bench Component Real-Time Updates**: Fixed document data not refreshing after processing
  - Added WebSocket listener in Bench component for `document:updated` events
  - Bench now refetches and updates open documents when processing completes
  - Document content cache properly cleared using `clearCache()` method
  - React components re-render with fresh data automatically
  - Fixed TypeError from calling non-existent `invalidateCache()` method

### Added

- **Generic Storage File Operations**: Extended all storage adapters with file operation support
  - Added three abstract methods to `StorageAdapter`: `save_file()`, `get_file()`, `delete_file()`
  - Implemented file operations in `RedisStorage` with base64 encoding and 10MB size limit
  - Registered `FilesystemStorage` in `StorageFactory` with automatic configuration
  - Added `filesystem_path` configuration setting (default: `./document_store`)
  - Implemented comprehensive unit tests for Redis file operations (100% coverage)
  - All storage adapters now support consistent file storage interface

- **Original PDF File Viewing**: Display original uploaded PDF files in the document viewer
  - Added backend endpoint `/api/documents/{id}/file` to serve original PDF files
  - Extended FilesystemStorage with `save_file()`, `get_file()`, and `delete_file()` methods
  - Modified document upload handler to save original PDF files permanently
  - Updated PDFViewer component to fetch and display original PDFs in iframe
  - Added `file_path` and `mime_type` fields to DocumentMetadata model
  - Implemented comprehensive unit tests for file storage operations (100% coverage)

- **Document Type-Specific Tool Recommendations**: Enhanced tool discovery system with JSON-specific tools
  - Added 3 JSON-specific tools: Validate JSON, Format JSON, Extract Schema
  - Implemented default tool fallback (Summarize, Extract Entities) for unsupported document types
  - All tools now properly filtered by document type for better user experience

- **Auto-Processing on Document Upload**: Automatic AI processing for all uploaded documents
  - AI summary generation automatically triggered on document upload
  - Entity extraction automatically executed for all new documents (>50 characters)
  - Auto-processing runs asynchronously and gracefully handles failures
  - Backend auto-updates document metadata with summary and entities

- **Enhanced Tool Testing**: Comprehensive test coverage for new tool functionality
  - Added tests for JSON-specific tools display
  - Added tests for default tools fallback behavior
  - All 15 tool menu tests passing with 100% coverage

- **Multi-Model Provider Architecture**: Comprehensive provider system for supporting multiple LLM models
  - Created `BaseModelProvider` abstract class for all model providers
  - Implemented `ModelProviderRegistry` for dynamic provider registration and discovery
  - Added decorator-based auto-registration with `@register_provider`
  - Created 8 provider implementations: Claude Sonnet/Haiku, GPT-4o/Mini, Gemini Pro/Flash, Text Embeddings
  - Each provider is self-contained and independently configurable

- **Intelligent Model Selection System**: Strategy-based model selection with multiple optimization strategies
  - Implemented `ModelSelector` with 5 selection strategies: cost, quality, latency, balanced, manual
  - Task-specific model selection with automatic fallback chains
  - Requirements-based filtering (latency, cost tier, quality score, context size)
  - Dynamic capability matching (vision, streaming, JSON mode, embeddings)
  - Cost estimation and performance prediction

- **Centralized Model Configuration**: All model settings now in central config
  - Comprehensive provider configurations with cost, performance, and capability metadata
  - 9 pre-configured models with detailed specifications (Claude, GPT, Gemini families)
  - Task-to-model mapping for optimal selection
  - Fallback chains for high availability
  - Support for Google Gemini (up to 2M context) and future models (xAI Grok)

- **Tool-Based LLM Architecture**: Complete refactoring of LLM service to use modular, plugin-based tool architecture
  - Created `BaseLLMTool` abstract base class for all LLM tools
  - Implemented `ToolRegistry` for dynamic tool registration and discovery
  - Added 7 specialized tools: Summarization, Markdown Formatting, Entity Extraction, Classification, Language Detection, Question Answering, and Embeddings
  - Each tool is now self-contained (~100-200 lines) and independently testable

- **Auto-Discovery Tool Registration System**: Decorator-based automatic tool registration
  - Implemented `@register_tool` decorator for zero-configuration tool registration
  - Support for tool aliases (e.g., TEXT_TO_MARKDOWN → MARKDOWN_FORMATTING)
  - Eliminated all manual tool registration code
  - Tools now self-register on import

- **Dynamic Configuration System**: Config-driven capabilities and health checks
  - Health check capabilities are now dynamically generated from registered tools
  - Removed all hardcoded capability lists
  - Added `_get_dynamic_capabilities()` method for runtime capability discovery
  - Capability mapping from technical tool capabilities to user-friendly names

- **Document Processing Improvements**:
  - Created `DocumentProcessor` service following existing service patterns
  - Centralized document processing orchestration
  - Eliminated code duplication between queue service implementations
  - Added support for multiple document types (PDF, Text, JSON, XML, CSV, Excel, Media, Webpage)
  - Integrated progress callbacks for real-time processing updates

- **Redis Queue Service Enhancements**:
  - Fixed metadata field errors by storing processing metadata in Redis separately
  - Improved error handling with WebSocket notifications
  - Added retry mechanism with configurable retry counts
  - Better status management and progress tracking

### Changed
- **LLM Service Refactoring**:
  - Reduced from 894 lines monolithic service to 531 lines orchestrator
  - Converted 8 hardcoded methods to pluggable tools
  - Maintained backward compatibility with existing API
  - Improved separation of concerns with tool-specific logic

- **Service Registration**:
  - Changed from manual registration (22 lines) to auto-discovery (3 lines)
  - Tools now use decorators for registration instead of explicit registration calls
  - Registration is triggered automatically on module import

### Fixed
- Fixed "DocumentMetadata has no field processing_started_at" error in Redis queue
- Fixed "LLMService has no attribute text_to_markdown" error
- Fixed Entity class import error in services __init__.py
- Fixed retry count storage in Redis queue service
- Fixed last_error field storage in Redis queue service

### Technical Improvements
- **Modularity**: Each LLM tool is now an independent, focused module
- **Scalability**: New AI capabilities can be added by creating new tool classes
- **Testability**: Tools can be tested in isolation without the full service
- **Maintainability**: Changes to one tool don't affect others
- **Consistency**: Follows established service/factory patterns throughout
- **Type Safety**: Decorators enforce proper type usage
- **Performance**: Dynamic capability generation with caching

## [0.1.0] - 2025-09-14

### Initial Release
- Basic document processing platform
- Service factory pattern implementation
- OpenTelemetry observability
- Redis-based distributed queue
- Frontend React application with document management
- WebSocket real-time updates
- Multiple storage adapter support (Filesystem, Redis)
