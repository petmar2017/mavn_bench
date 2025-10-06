# Document Tools System Design

## Overview

The Document Tools System is a decorator-based architecture for processing and analyzing documents, following the established LLM tool pattern. It provides dynamic tool discovery, intelligent recommendations, and seamless integration with the existing service infrastructure.

## Architecture Components

### 1. Base Infrastructure

#### BaseDocumentTool (`/backend/src/services/document_tools/base_tool.py`)

Abstract base class defining the interface for all document processing tools:

```python
class BaseDocumentTool(ABC):
    def __init__(self, tool_id, document_service=None, llm_service=None,
                 vector_search_service=None, **kwargs):
        # Dependency injection for service access

    @abstractmethod
    async def execute(self, document: DocumentMessage,
                     parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        # Core tool execution logic

    @abstractmethod
    def get_metadata(self) -> DocumentToolMetadata:
        # Tool capabilities, schemas, and requirements

    def get_recommendations_for_document(self, document: DocumentMessage) -> Dict[str, Any]:
        # Intelligent scoring for tool recommendations
```

**Key Features**:
- **Dependency Injection**: Services injected via constructor
- **Input Validation**: Automatic parameter and document type validation
- **Recommendation Engine**: Built-in scoring for document compatibility
- **Error Handling**: Comprehensive validation and error reporting
- **Metadata System**: Rich metadata for capabilities and requirements

#### DocumentToolMetadata

Comprehensive metadata system for describing tool capabilities:

```python
@dataclass
class DocumentToolMetadata:
    id: str
    name: str
    description: str
    category: DocumentToolCategory
    icon: str
    capabilities: List[DocumentToolCapability]
    supported_document_types: List[DocumentType]
    requires_llm: bool
    requires_vector_search: bool
    execution_time_estimate: str
    batch_capable: bool
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
```

### 2. Registry System

#### DocumentToolRegistry (`/backend/src/services/document_tools/tool_registry.py`)

Central registry for tool management and discovery:

```python
class DocumentToolRegistry:
    @classmethod
    def register(cls, tool_type: DocumentToolType, tool_class: Type[BaseDocumentTool]):
        # Register tool class for factory creation

    @classmethod
    def create(cls, tool_type: DocumentToolType, **services) -> BaseDocumentTool:
        # Create tool instance with dependency injection

    @classmethod
    def get_recommendations_for_document(cls, document: DocumentMessage, **services) -> List[Dict]:
        # Get ranked tool recommendations for document

    @classmethod
    def find_tools_by_document_type(cls, document_type: DocumentType) -> List[DocumentToolType]:
        # Find compatible tools for document type

    @classmethod
    def find_tools_by_capability(cls, capability: DocumentToolCapability) -> List[DocumentToolType]:
        # Find tools with specific capability
```

**Key Features**:
- **Singleton Management**: Efficient instance management
- **Dynamic Discovery**: Runtime tool discovery and filtering
- **Compatibility Checking**: Document type and service requirement validation
- **Statistics**: Comprehensive registry statistics and health monitoring

### 3. Auto-Registration System

#### @register_document_tool Decorator (`/backend/src/services/document_tools/tool_decorators.py`)

Automatic tool discovery and registration:

```python
@register_document_tool(DocumentToolType.VALIDATE_JSON)
class ValidateJSONTool(BaseDocumentTool):
    # Tool implementation automatically discovered and registered

def initialize_document_tools():
    # Scan modules and register all decorated tools
    # Called during application startup
```

**Key Features**:
- **Zero Configuration**: Tools auto-discovered on startup
- **Module Scanning**: Automatic import of tool modules
- **Alias Support**: Tools can handle multiple tool types
- **Initialization Statistics**: Detailed startup reporting

### 4. Tool Implementations

#### ValidateJSON Tool
- **Purpose**: JSON syntax and schema validation
- **Features**: Deep nesting analysis, type consistency checking, statistics generation
- **Capabilities**: VALIDATION, QUALITY_CHECK
- **Document Types**: JSON

#### Sentiment Analysis Tool
- **Purpose**: Emotional tone and sentiment analysis using LLM
- **Features**: Multi-granularity analysis, aspect-based sentiment, emotion detection
- **Capabilities**: ANALYSIS, CLASSIFICATION
- **Document Types**: TEXT, MARKDOWN, PDF, WORD, WEBPAGE
- **Requirements**: LLM service

#### Find Similar Documents Tool
- **Purpose**: Vector-based document similarity search
- **Features**: Vector similarity, keyword fallback, similarity scoring
- **Capabilities**: SIMILARITY, ANALYSIS
- **Document Types**: All text-based types
- **Requirements**: Vector search service

### 5. API Integration

#### Tools Router (`/backend/src/api/routers/tools.py`)

RESTful API for tool management and execution:

```
GET    /api/tools                     # List all available tools
GET    /api/tools/{tool_type}         # Get specific tool info
POST   /api/tools/recommendations     # Get tool recommendations
POST   /api/tools/execute             # Execute tool on document
GET    /api/tools/categories          # List tool categories
GET    /api/tools/capabilities        # List tool capabilities
```

**Key Features**:
- **Tool Discovery**: Comprehensive tool listing and filtering
- **Intelligent Recommendations**: AI-powered tool suggestions
- **Execution Engine**: Validated tool execution with error handling
- **Performance Monitoring**: Execution time tracking and health checks

## Tool Categories and Capabilities

### Categories
- **CONTENT_PROCESSING**: Text analysis and transformation
- **DATA_VALIDATION**: Format and schema validation
- **FORMAT_CONVERSION**: Document format transformation
- **ANALYSIS**: Content analysis and insights
- **ENHANCEMENT**: Content improvement and enrichment
- **SEARCH**: Document discovery and similarity
- **QUALITY**: Quality assessment and improvement
- **METADATA**: Metadata extraction and enrichment

### Capabilities
- **VALIDATION**: Document and data validation
- **TRANSFORMATION**: Content transformation
- **ANALYSIS**: Content analysis and insights
- **EXTRACTION**: Information extraction
- **ENHANCEMENT**: Content improvement
- **SIMILARITY**: Similarity and matching
- **CLASSIFICATION**: Content classification
- **FORMATTING**: Format improvement
- **QUALITY_CHECK**: Quality assessment
- **METADATA_ENRICHMENT**: Metadata enhancement

## Integration with Existing Systems

### Service Factory Integration

Tools integrate seamlessly with the existing service factory pattern:

```python
# Tools receive services via dependency injection
tool = DocumentToolRegistry.create(
    DocumentToolType.SENTIMENT_ANALYSIS,
    document_service=ServiceFactory.create(ServiceType.DOCUMENT),
    llm_service=ServiceFactory.create(ServiceType.LLM),
    vector_search_service=ServiceFactory.create(ServiceType.VECTOR_SEARCH)
)
```

### OpenTelemetry Integration

All tool operations are automatically traced:

```python
# Built into API router
with traced_operation("execute_tool", document_id=..., tool_type=...):
    result = await tool.execute_with_validation(document, parameters)
```

### Configuration Integration

Tools integrate with the existing configuration system:

```python
# Tool-specific configuration
document_tools:
  sentiment_analysis:
    confidence_threshold: 0.7
    granularity: "paragraph"
  validate_json:
    strict_mode: false
```

## Recommendation Engine

The system includes an intelligent recommendation engine that scores tools based on:

1. **Document Type Compatibility**: 40% weight
2. **Content Characteristics**: 30% weight
3. **Service Availability**: 20% weight
4. **User Context**: 10% weight

### Scoring Algorithm

```python
def get_recommendations_for_document(self, document: DocumentMessage) -> Dict[str, Any]:
    score = 0.5  # Base compatibility score

    # Document type compatibility
    if not self.supports_document_type(document.metadata.document_type):
        return {"score": 0.0, "applicable": False}

    # Content-based scoring
    if document.content and document.content.text:
        if len(document.content.text) > 1000 and ANALYSIS in capabilities:
            score += 0.2

    # Service availability
    if metadata.requires_llm and not self.llm_service:
        score *= 0.3

    return {"score": min(score, 1.0), "applicable": score > 0.3}
```

## Performance Characteristics

### Execution Time Estimates
- **Fast**: < 1 second (validation, simple analysis)
- **Medium**: 1-10 seconds (LLM-based analysis)
- **Slow**: > 10 seconds (complex multi-step operations)

### Scalability Features
- **Singleton Pattern**: Efficient service reuse
- **Batch Processing**: Support for batch operations where applicable
- **Service Pooling**: Connection pooling for external services
- **Caching**: Result caching for expensive operations

## Security and Validation

### Input Validation
- **Type Checking**: Automatic parameter type validation
- **Schema Validation**: Input/output schema enforcement
- **Document Type Checking**: Compatibility validation
- **Service Requirement Validation**: Required service availability

### Error Handling
- **Graceful Degradation**: Fallback mechanisms for service failures
- **Detailed Error Messages**: Comprehensive error reporting
- **Audit Logging**: All operations logged with trace context
- **Rate Limiting**: Protection against abuse

## Testing Strategy

### Tool Testing
```python
@pytest.mark.asyncio
async def test_validate_json_tool():
    # Create tool with real services
    tool = DocumentToolRegistry.create(DocumentToolType.VALIDATE_JSON)

    # Test with real JSON document
    document = create_test_document(DocumentType.JSON, '{"valid": true}')
    result = await tool.execute(document)

    assert result["valid"] is True
    assert "statistics" in result
```

### API Testing
```python
async def test_tool_recommendations():
    response = await client.post("/api/tools/recommendations", json={
        "document_id": "test-doc-123",
        "max_recommendations": 5
    })

    assert response.status_code == 200
    recommendations = response.json()
    assert len(recommendations) <= 5
    assert all("score" in rec for rec in recommendations)
```

## Extension Points

### Adding New Tools

1. **Create Tool Class**:
```python
@register_document_tool(DocumentToolType.NEW_TOOL)
class NewTool(BaseDocumentTool):
    def get_metadata(self) -> DocumentToolMetadata:
        return DocumentToolMetadata(...)

    async def execute(self, document, parameters=None):
        return {"result": "..."}
```

2. **Add to Registry**: Tool automatically registered on startup

3. **Update API**: No API changes needed - automatic discovery

### Adding New Categories/Capabilities

1. **Extend Enums**:
```python
class DocumentToolCategory(str, Enum):
    NEW_CATEGORY = "new_category"

class DocumentToolCapability(str, Enum):
    NEW_CAPABILITY = "new_capability"
```

2. **Update Documentation**: Add descriptions and use cases

## Migration from Legacy System

The system includes a comprehensive migration plan in `DOCUMENT_TOOLS_MIGRATION_PLAN.md` that covers:

1. **Phase 1**: Wrapper tools for existing functionality
2. **Phase 2**: API compatibility layer
3. **Phase 3**: Enhanced native implementations
4. **Phase 4**: Client migration
5. **Phase 5**: Legacy removal

This ensures zero-downtime migration while providing enhanced capabilities.

## Monitoring and Observability

### Metrics
- **Tool Usage**: Execution counts by tool type
- **Performance**: Execution times and success rates
- **Recommendations**: Recommendation accuracy and adoption
- **Errors**: Error rates and types by tool

### Health Checks
```python
GET /api/tools/health
{
    "status": "healthy",
    "total_tools": 15,
    "statistics": {...},
    "available_tools": [...]
}
```

### Tracing
All operations include OpenTelemetry traces with:
- Tool type and document ID
- Execution time and success status
- Service dependencies and performance
- Error details and stack traces

## Future Enhancements

1. **Workflow Tools**: Multi-step tool orchestration
2. **Machine Learning**: ML-based recommendation improvement
3. **Plugin System**: External tool integration
4. **Batch Processing**: Enhanced batch operation support
5. **Caching Layer**: Advanced result caching
6. **Real-time Processing**: Stream processing capabilities

## Conclusion

The Document Tools System provides a robust, extensible architecture for document processing that:

- **Follows Established Patterns**: Based on proven LLM tool architecture
- **Enables Dynamic Discovery**: Tools automatically discovered and registered
- **Provides Intelligent Recommendations**: AI-powered tool suggestions
- **Integrates Seamlessly**: Works with existing service infrastructure
- **Ensures Quality**: Comprehensive validation and error handling
- **Supports Migration**: Zero-downtime migration from legacy systems
- **Enables Innovation**: Easy extension with new tools and capabilities

The system is production-ready and provides a solid foundation for current and future document processing needs.