# Changelog

All notable changes to the Mavn Bench project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 2025-09-15

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
