# Mavn Bench - System Architecture Document

## Executive Summary
Mavn Bench is a comprehensive document processing platform designed with enterprise-grade architecture principles. It employs strict service and factory patterns, event-driven communication, and full observability through OpenTelemetry. The system is built for Python 3.13+ with async/await throughout for optimal performance.

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Design Principles](#design-principles)
3. [System Components](#system-components)
4. [Design Patterns](#design-patterns)
5. [Data Flow](#data-flow)
6. [Technology Stack](#technology-stack)
7. [Security Architecture](#security-architecture)
8. [Scalability & Performance](#scalability--performance)
9. [Deployment Architecture](#deployment-architecture)

## Architecture Overview

### High-Level Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                          Client Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ React Web UI │  │   REST API   │  │  WebSocket   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                          API Gateway                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │Auth Middleware│  │Rate Limiting │  │  Telemetry   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Service Layer                              │
│  ┌────────────────────────────────────────────────────┐        │
│  │              Service Factory                        │        │
│  └────────────────────────────────────────────────────┘        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ Document │  │   PDF    │  │   LLM    │  │   MCP    │      │
│  │ Service  │  │ Service  │  │ Service  │  │ Service  │      │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │Transcript│  │ Scraping │  │  Vector  │  │  Graph   │      │
│  │ Service  │  │ Service  │  │  Search  │  │  Search  │      │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
└─────────────────────────────────────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Storage Layer                              │
│  ┌────────────────────────────────────────────────────┐        │
│  │              Storage Factory                        │        │
│  └────────────────────────────────────────────────────┘        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │  Filesystem  │  │    Redis     │  │  PostgreSQL  │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└─────────────────────────────────────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    External Services                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │  OpenAI  │  │ Anthropic│  │  Qdrant  │  │   Neo4j  │      │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

### Component Interaction Diagram
```
     Frontend                  Backend                    Storage
        │                         │                          │
        ├──Document Upload───────▶│                          │
        │                         ├──Validate & Store───────▶│
        │                         │◀─────────ACK─────────────┤
        │                         ├──Process Document        │
        │                         │  (Async Task)            │
        │                         ├──Extract Content         │
        │                         ├──Generate Embeddings     │
        │                         ├──Index for Search────────▶│
        │◀────WebSocket Event─────┤                          │
        │                         │                          │
        ├──Search Request────────▶│                          │
        │                         ├──Query Vector DB─────────▶│
        │                         │◀────Results──────────────┤
        │◀────Search Results──────┤                          │
```

## Design Principles

### 1. Service-Oriented Architecture (SOA)
- Each business capability is encapsulated in a service
- Services are loosely coupled and highly cohesive
- Communication through well-defined interfaces

### 2. Factory Pattern Implementation
```python
# Strict factory pattern for all major components
class ServiceFactory:
    """Factory for creating service instances"""
    _services: Dict[str, Type[BaseService]] = {}
    
    @classmethod
    def register(cls, service_type: str, service_class: Type[BaseService]):
        cls._services[service_type] = service_class
    
    @classmethod
    def create(cls, service_type: str, **kwargs) -> BaseService:
        service_class = cls._services.get(service_type)
        if not service_class:
            raise ValueError(f"Unknown service type: {service_type}")
        return service_class(**kwargs)
```

### 3. Dependency Injection
```python
# All dependencies injected through constructors
class DocumentService(BaseService):
    def __init__(
        self,
        storage: StorageAdapter,
        llm_service: LLMService,
        pdf_service: PDFService,
        logger: CentralizedLogger
    ):
        super().__init__("DocumentService")
        self.storage = storage
        self.llm_service = llm_service
        self.pdf_service = pdf_service
        self.logger = logger
```

### 4. Async-First Design
- All I/O operations are async
- No blocking calls in request path
- Proper connection pooling
- Background task processing

### 5. Event-Driven Communication
```python
# Document events propagated through WebSocket
class DocumentEventBus:
    async def emit(self, event: DocumentEvent):
        """Emit event to all subscribers"""
        for subscriber in self.subscribers:
            await subscriber.notify(event)
```

## System Components

### 1. API Layer

#### FastAPI Application
- **Purpose**: HTTP API gateway
- **Responsibilities**:
  - Request routing
  - Input validation
  - Response serialization
  - WebSocket management
- **Key Features**:
  - Automatic OpenAPI documentation
  - Request/response validation with Pydantic
  - Async request handling
  - WebSocket support for real-time events

#### Middleware Stack
```python
# Middleware execution order
app.add_middleware(CORSMiddleware)        # 1. CORS handling
app.add_middleware(TelemetryMiddleware)   # 2. Tracing & metrics
app.add_middleware(AuthMiddleware)        # 3. Authentication
app.add_middleware(RateLimitMiddleware)   # 4. Rate limiting
app.add_middleware(ErrorHandlerMiddleware)# 5. Error handling
```

### 2. Service Layer

#### Base Service Pattern
```python
class BaseService(ABC):
    """Abstract base service with common functionality"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.tracer = trace.get_tracer(service_name)
        self.logger = CentralizedLogger(service_name)
        self.metrics = MetricsCollector(service_name)
    
    @contextmanager
    def traced_operation(self, operation_name: str, **attributes):
        """Automatic tracing for all operations"""
        with self.tracer.start_as_current_span(operation_name) as span:
            span.set_attributes(attributes)
            try:
                yield span
            except Exception as e:
                span.record_exception(e)
                raise
    
    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """Each service must implement health check"""
        pass
```

#### Document Processing Services

**PDFService**
```python
class PDFService(BaseService):
    """PDF processing and conversion service"""
    
    async def pdf_to_markdown(self, file_path: str) -> str:
        """Convert PDF to markdown with structure preservation"""
        with self.traced_operation("pdf_to_markdown", file_path=file_path):
            # 1. Extract text with PyMuPDF
            # 2. Detect layout and structure
            # 3. Convert tables to markdown
            # 4. Preserve formatting
            # 5. Extract images (optional)
            return markdown_content
    
    async def extract_tables(self, file_path: str) -> List[pd.DataFrame]:
        """Extract tables as DataFrames"""
        # Table detection and extraction logic
```

**TranscriptionService**
```python
class TranscriptionService(BaseService):
    """Audio/video transcription service"""
    
    async def transcribe_youtube(self, url: str) -> DocumentMessage:
        """Download and transcribe YouTube video"""
        with self.traced_operation("transcribe_youtube", url=url):
            # 1. Download audio with yt-dlp
            # 2. Convert to supported format
            # 3. Send to Whisper API
            # 4. Process transcript
            # 5. Create DocumentMessage
            return document
    
    async def transcribe_podcast(self, url: str) -> DocumentMessage:
        """Transcribe podcast from URL"""
        # Similar flow for podcasts
```

**LLMService - Tool-Based Architecture**
```python
class LLMService(BaseService):
    """LLM service using modular tool-based architecture"""

    def __init__(self):
        super().__init__("LLMService")
        # Auto-register all tools using decorators
        self._register_tools()

    def _register_tools(self):
        """Auto-discovery tool registration"""
        from .llm import tools  # Triggers decorator registration
        from .llm.tool_decorators import auto_register_decorated_tools
        num_registered = auto_register_decorated_tools()
        self.logger.info(f"Auto-registered {num_registered} tools")

    async def execute_tool(
        self,
        tool_type: LLMToolType,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a specific tool with dynamic dispatch"""
        tool = ToolRegistry.create(tool_type, self.llm_client)
        return await tool.execute(input_data)

    def _get_dynamic_capabilities(self) -> List[str]:
        """Generate capabilities from registered tools"""
        capabilities = set()
        for tool_type in ToolRegistry.get_available_tools():
            metadata = ToolRegistry.get_tool_metadata(tool_type)
            # Map tool capabilities to service capabilities
            capabilities.update(self._map_capabilities(metadata))
        return sorted(list(capabilities))
```

#### LLM Tool Architecture

The LLM service has been refactored from a monolithic 894-line service to a modular, plugin-based architecture:

**Tool Components:**
- **BaseLLMTool**: Abstract base class defining the tool interface
- **ToolRegistry**: Central registry for tool discovery and creation
- **Tool Decorators**: Auto-registration system using Python decorators
- **Specialized Tools**: 7 focused tools (Summarization, Entity Extraction, etc.)

**Auto-Registration System:**
```python
# Tool implementation with decorator
@register_tool(LLMToolType.SUMMARIZATION)
class SummarizationTool(BaseLLMTool):
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # Tool-specific logic
        pass

# Auto-discovery eliminates manual registration
# Old: 22 lines of manual registration
# New: 3 lines of auto-discovery
```

**Benefits:**
- **Modularity**: Each tool is ~100-200 lines and independently testable
- **Scalability**: New capabilities added by creating new tool classes
- **Maintainability**: Changes to one tool don't affect others
- **Type Safety**: Decorators enforce proper type usage
- **Dynamic Configuration**: Capabilities generated from registered tools

#### Multi-Model Provider Architecture

The LLM service now supports multiple model providers through a comprehensive provider system:

**Provider Components:**
- **BaseModelProvider**: Abstract base class defining provider interface
- **ModelProviderRegistry**: Central registry for provider discovery
- **ModelSelector**: Intelligent model selection with strategies
- **Provider Implementations**: 8+ providers (Claude, GPT, Gemini families)

**Model Selection Strategies:**
```python
class SelectionStrategy(Enum):
    COST = "cost"          # Minimize cost
    QUALITY = "quality"    # Maximize quality
    LATENCY = "latency"    # Minimize latency
    BALANCED = "balanced"  # Balance all factors
    MANUAL = "manual"      # Use explicit overrides

# Intelligent selection based on requirements
selector = ModelSelector()
model = selector.select_model(
    task_type=LLMToolType.SUMMARIZATION,
    requirements=TaskRequirements(
        max_latency_ms=1000,
        max_cost_tier=CostTier.STANDARD,
        min_quality_score=0.8
    )
)
```

**Configuration-Driven Providers:**
All provider settings are centralized in config:
```python
providers: {
    "anthropic-claude-3.5-sonnet": {
        "name": "Claude 3.5 Sonnet",
        "cost_per_1k_input": 0.003,
        "cost_per_1k_output": 0.015,
        "cost_tier": "premium",
        "avg_latency_ms": 2000,
        "max_context": 200000,
        "quality_score": 0.95,
        "capabilities": "text_generation,long_context,json_mode",
        "preferred_for": "complex_reasoning,detailed_analysis"
    },
    # ... more providers
}
```

**Provider Registration:**
```python
@register_provider("anthropic-claude-3.5-sonnet")
class ClaudeSonnetProvider(BaseModelProvider):
    # Provider implementation
    pass
```

**Benefits:**
- **Multi-Model Support**: Easy integration of new models (Gemini, Grok, Llama, etc.)
- **Cost Optimization**: Automatic selection based on cost/performance requirements
- **High Availability**: Fallback chains ensure service continuity
- **Config-Driven**: All settings in central configuration
- **Future-Proof**: Ready for new models without code changes

### 3. Storage Layer

#### Storage Adapter Pattern
```python
class StorageAdapter(ABC):
    """Abstract storage adapter"""
    
    @abstractmethod
    async def save(self, doc_id: str, content: Dict[str, Any]) -> bool:
        pass
    
    @abstractmethod
    async def load(self, doc_id: str) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def delete(self, doc_id: str) -> bool:
        pass
    
    @abstractmethod
    async def list_documents(self, filter: DocumentFilter) -> List[str]:
        pass
```

#### Filesystem Storage
```python
class FilesystemStorage(StorageAdapter):
    """File-based storage implementation"""
    
    def __init__(self, base_path: str = "/document_store"):
        self.base_path = Path(base_path)
    
    async def save(self, doc_id: str, content: Dict[str, Any]) -> bool:
        """Save document to filesystem"""
        doc_path = self.base_path / doc_id / "document.json"
        async with aiofiles.open(doc_path, 'w') as f:
            await f.write(json.dumps(content))
        return True
```

#### Redis Storage
```python
class RedisStorage(StorageAdapter):
    """Redis-based storage implementation"""
    
    def __init__(self, redis_url: str):
        self.redis = aioredis.from_url(redis_url)
    
    async def save(self, doc_id: str, content: Dict[str, Any]) -> bool:
        """Save document to Redis"""
        return await self.redis.set(
            f"doc:{doc_id}", 
            json.dumps(content),
            ex=86400  # 24 hour TTL
        )
```

### 4. Queue Architecture

#### Distributed Queue Service
```python
class QueueService(BaseService):
    """Redis-based distributed queue for horizontal scaling"""

    def __init__(self):
        super().__init__("QueueService")
        self.redis = Redis.from_url(settings.redis.url)
        self.active_workers = {}

    async def enqueue_document(
        self,
        document: DocumentMessage,
        priority: ProcessingPriority = ProcessingPriority.NORMAL
    ) -> str:
        """Add document to processing queue"""
        task_id = str(uuid.uuid4())

        # Store document in Redis
        await self.redis.hset(
            f"doc:{document.metadata.document_id}",
            mapping=document.model_dump_json()
        )

        # Add to priority queue
        queue_name = f"queue:{priority.value}"
        await self.redis.lpush(queue_name, task_id)

        # Track processing status
        await self._update_status(task_id, ProcessingStatus.QUEUED)

        return task_id
```

#### Worker Pool Architecture
```python
class WorkerPool:
    """Manages distributed workers for document processing"""

    def __init__(self, pool_size: int = 4):
        self.pool_size = pool_size
        self.workers = []

    async def start(self):
        """Start worker pool"""
        for i in range(self.pool_size):
            worker = DocumentWorker(worker_id=f"worker-{i}")
            self.workers.append(worker)
            asyncio.create_task(worker.run())

    async def scale(self, new_size: int):
        """Dynamically scale worker pool"""
        if new_size > self.pool_size:
            # Add workers
            for i in range(self.pool_size, new_size):
                worker = DocumentWorker(worker_id=f"worker-{i}")
                self.workers.append(worker)
                asyncio.create_task(worker.run())
        elif new_size < self.pool_size:
            # Remove workers gracefully
            workers_to_remove = self.workers[new_size:]
            for worker in workers_to_remove:
                await worker.shutdown()
```

#### Document Processor Service
```python
class DocumentProcessor(BaseService):
    """Centralized document processing orchestration"""

    async def process_document(
        self,
        document: DocumentMessage,
        progress_callback: Optional[Callable] = None
    ) -> DocumentMessage:
        """Process document through appropriate pipeline"""

        # Determine processing strategy
        strategy = self._get_processing_strategy(document.metadata.doc_type)

        # Execute processing pipeline
        pipeline = [
            ("extract", self._extract_content),
            ("convert", self._convert_format),
            ("enhance", self._enhance_with_ai),
            ("index", self._index_for_search),
        ]

        for step_name, step_func in pipeline:
            try:
                document = await step_func(document)
                if progress_callback:
                    await progress_callback(step_name, document)
            except Exception as e:
                self.logger.error(f"Pipeline step {step_name} failed: {e}")
                document.metadata.processing_errors.append({
                    "step": step_name,
                    "error": str(e),
                    "timestamp": datetime.utcnow()
                })

        return document
```

#### Priority Queue Management
```python
class ProcessingPriority(Enum):
    URGENT = "urgent"      # < 1 minute
    HIGH = "high"          # < 5 minutes
    NORMAL = "normal"      # < 15 minutes
    LOW = "low"            # Best effort

class PriorityQueueManager:
    """Manages multiple priority queues"""

    async def get_next_task(self) -> Optional[Task]:
        """Get next task respecting priorities"""
        # Check queues in priority order
        for priority in ProcessingPriority:
            queue_name = f"queue:{priority.value}"
            task_id = await self.redis.rpop(queue_name)
            if task_id:
                return await self._load_task(task_id)
        return None
```

#### Queue Features
- **Horizontal Scaling**: Add workers dynamically based on load
- **Priority Processing**: Multiple priority levels with SLA guarantees
- **Retry Mechanism**: Configurable retry with exponential backoff
- **Dead Letter Queue**: Failed tasks moved to DLQ for investigation
- **Progress Tracking**: Real-time progress updates via WebSocket
- **Graceful Shutdown**: Workers complete current tasks before stopping

### 5. Search Services

#### Vector Search Architecture
```python
class VectorSearchService(BaseService):
    """Vector similarity search using Qdrant"""
    
    def __init__(self, qdrant_url: str):
        super().__init__("VectorSearchService")
        self.client = QdrantClient(qdrant_url)
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    async def index_document(self, doc_id: str, content: str):
        """Generate embeddings and index document"""
        embeddings = self.embedding_model.encode(content)
        await self.client.upsert(
            collection_name="documents",
            points=[
                PointStruct(
                    id=doc_id,
                    vector=embeddings.tolist(),
                    payload={"content": content}
                )
            ]
        )
    
    async def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Perform vector similarity search"""
        query_vector = self.embedding_model.encode(query)
        results = await self.client.search(
            collection_name="documents",
            query_vector=query_vector.tolist(),
            limit=limit
        )
        return [SearchResult.from_qdrant(r) for r in results]
```

## Design Patterns

### 1. Factory Pattern
Used for creating instances of services, storage adapters, and processors.

```python
# Service registration
ServiceFactory.register("pdf", PDFService)
ServiceFactory.register("llm", LLMService)
ServiceFactory.register("transcription", TranscriptionService)

# Service creation
pdf_service = ServiceFactory.create("pdf", config=pdf_config)
```

### 2. Adapter Pattern
Used for storage abstraction and external service integration.

```python
# Storage adapter allows switching backends
storage = StorageFactory.create(
    settings.storage.type,  # "filesystem" or "redis"
    **settings.storage.dict()
)
```

### 3. Observer Pattern
Used for event-driven communication between components.

```python
# Event subscription
event_bus.subscribe("document.created", index_service.handle_new_document)
event_bus.subscribe("document.updated", cache_service.invalidate)

# Event emission
await event_bus.emit(DocumentEvent(
    type="document.created",
    document_id=doc_id,
    user_id=user_id
))
```

### 4. Strategy Pattern
Used for different processing strategies based on document type.

```python
class ProcessingStrategy(ABC):
    @abstractmethod
    async def process(self, document: DocumentMessage) -> DocumentMessage:
        pass

class PDFProcessingStrategy(ProcessingStrategy):
    async def process(self, document: DocumentMessage) -> DocumentMessage:
        # PDF-specific processing
        pass

class VideoProcessingStrategy(ProcessingStrategy):
    async def process(self, document: DocumentMessage) -> DocumentMessage:
        # Video transcription and processing
        pass
```

### 5. Repository Pattern
Used for data access abstraction.

```python
class DocumentRepository:
    """Repository for document data access"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, doc_id: str) -> Optional[Document]:
        """Get document by ID"""
        result = await self.session.execute(
            select(Document).where(Document.id == doc_id)
        )
        return result.scalar_one_or_none()
    
    async def save(self, document: Document) -> Document:
        """Save or update document"""
        self.session.add(document)
        await self.session.commit()
        return document
```

## Data Flow

### 1. Document Upload Flow
```
1. Client uploads file via REST API
2. API validates request and authentication
3. DocumentService receives file
4. File saved to storage (filesystem/Redis)
5. Background task queued for processing
6. Processing based on document type:
   - PDF: Extract text, tables, metadata
   - Audio/Video: Transcribe
   - Web: Scrape and convert to markdown
7. Generate embeddings for search
8. Index in vector/graph/fulltext search
9. Send completion event via WebSocket
10. Update UI with processed document
```

### 2. Search Flow
```
1. Client sends search query
2. Query parsed and enhanced
3. Parallel search execution:
   - Vector search for semantic similarity
   - Graph search for relationships
   - Fulltext search for exact matches
4. Results aggregated and ranked
5. Access control applied
6. Results returned to client
```

### 3. Tool Execution Flow
```
1. Client requests available tools for document
2. MCP Registry returns applicable tools
3. Client selects and executes tool
4. MCP Proxy forwards to tool server
5. Tool processes document
6. Results returned through proxy
7. Document updated with tool output
8. Event emitted for UI update
```

## Technology Stack

### Core Technologies
- **Language**: Python 3.13+
- **Framework**: FastAPI
- **Async**: asyncio, aiofiles, aiohttp
- **Database**: PostgreSQL/SQLite with SQLAlchemy
- **Cache**: Redis
- **Queue**: Celery with Redis broker

### Document Processing
- **PDF**: PyMuPDF, pdf2image, pdfplumber
- **Office**: python-docx, openpyxl
- **Web**: BeautifulSoup4, Playwright
- **Audio/Video**: yt-dlp, ffmpeg
- **Transcription**: OpenAI Whisper

### Search & AI
- **Vector DB**: Qdrant
- **Graph DB**: Neo4j
- **Fulltext**: Elasticsearch
- **LLM**: OpenAI, Anthropic
- **Embeddings**: Sentence Transformers

### Observability
- **Tracing**: OpenTelemetry
- **Metrics**: Prometheus
- **Logs**: Structured JSON
- **Visualization**: Jaeger, Grafana

### Testing
- **Unit**: pytest, pytest-asyncio
- **Coverage**: pytest-cov
- **Mocking**: NOT USED (real implementations only)
- **Load**: locust

## Security Architecture

### 1. Authentication
```python
# API Key authentication
class APIKeyAuth:
    async def __call__(self, request: Request) -> Optional[User]:
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            raise HTTPException(401, "API key required")
        
        user = await get_user_by_api_key(api_key)
        if not user:
            raise HTTPException(401, "Invalid API key")
        
        return user
```

### 2. Authorization
```python
# Role-based access control
class PermissionChecker:
    def __init__(self, required_permission: str):
        self.required_permission = required_permission
    
    async def __call__(self, user: User = Depends(get_current_user)):
        if not user.has_permission(self.required_permission):
            raise HTTPException(403, "Insufficient permissions")
        return user
```

### 3. Data Protection
- Encryption at rest for sensitive data
- TLS for all external communications
- Sanitization of user inputs
- SQL injection prevention with parameterized queries
- XSS protection in responses

### 4. Rate Limiting
```python
# Per-user rate limiting
@router.get("/api/documents")
@rate_limit(calls=100, period=timedelta(minutes=1))
async def list_documents(user: User = Depends(get_current_user)):
    # Implementation
```

## Scalability & Performance

### 1. Horizontal Scaling
- Stateless services for easy scaling
- Load balancing with nginx/HAProxy
- Database read replicas
- Redis cluster for caching

### 2. Performance Optimizations
- Connection pooling for databases
- Async I/O throughout
- Caching at multiple levels
- Lazy loading of large objects
- Pagination for list endpoints

### 3. Resource Management
```python
# Connection pool configuration
database_pool = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=3600
)
```

### 4. Background Processing
```python
# Celery task for heavy processing
@celery_app.task
async def process_document(doc_id: str):
    """Process document in background"""
    document = await load_document(doc_id)
    
    # Heavy processing
    await extract_text(document)
    await generate_embeddings(document)
    await index_for_search(document)
    
    # Notify completion
    await emit_event("document.processed", doc_id)
```

## Deployment Architecture

### 1. Container Architecture
```yaml
# docker-compose.yml
version: '3.8'
services:
  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db/mavn
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
  
  worker:
    build: ./backend
    command: celery worker
    environment:
      - CELERY_BROKER=redis://redis:6379
    depends_on:
      - redis
  
  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
```

### 2. Kubernetes Deployment
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mavn-bench-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mavn-bench-api
  template:
    metadata:
      labels:
        app: mavn-bench-api
    spec:
      containers:
      - name: api
        image: mavn-bench:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

### 3. CI/CD Pipeline
```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: |
          python -m pytest tests/ --cov=src --cov-report=xml
      - name: Check coverage
        run: |
          coverage report --fail-under=80

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Build and push Docker image
        run: |
          docker build -t mavn-bench:${{ github.sha }} .
          docker push mavn-bench:${{ github.sha }}
      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/mavn-bench-api api=mavn-bench:${{ github.sha }}
```

## Error Handling Strategy

### 1. Service-Level Error Handling
```python
class ServiceError(Exception):
    """Base exception for service errors"""
    pass

class DocumentNotFoundError(ServiceError):
    """Document not found"""
    pass

class ProcessingError(ServiceError):
    """Document processing failed"""
    pass

class ExternalServiceError(ServiceError):
    """External service failure"""
    pass
```

### 2. API Error Responses
```python
@app.exception_handler(ServiceError)
async def service_error_handler(request: Request, exc: ServiceError):
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.__class__.__name__,
            "message": str(exc),
            "trace_id": request.state.trace_id
        }
    )
```

### 3. Retry Strategy
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(ExternalServiceError)
)
async def call_external_service():
    """Call with automatic retry"""
    pass
```

## Monitoring & Alerting

### 1. Key Metrics
- Request rate and latency
- Error rate by endpoint
- Document processing time
- Queue length and processing rate
- Database connection pool usage
- Cache hit rate
- External service latency

### 2. Health Checks
```python
@router.get("/health")
async def health_check():
    """Comprehensive health check"""
    checks = {
        "database": await check_database(),
        "redis": await check_redis(),
        "storage": await check_storage(),
        "external_services": await check_external_services()
    }
    
    status = "healthy" if all(checks.values()) else "degraded"
    
    return {
        "status": status,
        "checks": checks,
        "version": settings.app_version,
        "timestamp": datetime.utcnow()
    }
```

### 3. Alerting Rules
- Response time > 1s for > 1% of requests
- Error rate > 1% for 5 minutes
- Queue backlog > 1000 items
- Database connection pool exhausted
- External service timeout rate > 5%

## Development Guidelines

### 1. Code Organization
```
backend/src/
├── api/           # API layer (FastAPI)
├── services/      # Business logic services
├── models/        # Data models
├── storage/       # Storage adapters
├── core/          # Core utilities
├── tasks/         # Background tasks
└── tests/         # Test files
```

### 2. Naming Conventions
- Classes: PascalCase (e.g., `DocumentService`)
- Functions: snake_case (e.g., `process_document`)
- Constants: UPPER_SNAKE_CASE (e.g., `MAX_FILE_SIZE`)
- Private methods: _leading_underscore (e.g., `_validate_input`)

### 3. Type Hints
```python
# Always use type hints
async def process_document(
    document: DocumentMessage,
    options: ProcessingOptions = None
) -> ProcessedDocument:
    """Process document with type safety"""
    pass
```

### 4. Testing Requirements
- Minimum 80% code coverage
- All public methods must have tests
- Integration tests for all API endpoints
- No mock objects - use real implementations
- Performance tests for critical paths

### 5. Documentation
- Docstrings for all public methods
- README in each module directory
- API documentation via OpenAPI
- Architecture decisions documented
- Changelog maintained

## Performance Benchmarks

### Target Metrics
- API Response Time: < 200ms (p95)
- Document Processing: < 30s for 10MB PDF
- Search Latency: < 100ms
- Concurrent Users: 100+
- Throughput: 1000 req/sec
- Availability: 99.9%

### Load Testing
```python
# Locust test example
class DocumentUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def list_documents(self):
        self.client.get("/api/documents")
    
    @task
    def upload_document(self):
        with open("test.pdf", "rb") as f:
            self.client.post("/api/documents/upload", files={"file": f})
```

## Future Enhancements

### Phase 1 (Q4 2025)
- Multi-language support
- Real-time collaboration
- Advanced OCR capabilities
- Mobile application

### Phase 2 (Q1 2026)
- Machine learning pipelines
- Custom model training
- Advanced analytics dashboard
- Plugin system for extensibility

### Phase 3 (Q2 2026)
- Federated learning
- Edge deployment
- Blockchain integration for audit trail
- Advanced security features (E2E encryption)

## Appendix

### A. Configuration Schema
```yaml
# Complete configuration structure
app:
  name: string
  version: string
  environment: enum[development, staging, production]

storage:
  type: enum[filesystem, redis, s3]
  filesystem:
    base_path: string
  redis:
    url: string
    ttl: integer
  s3:
    bucket: string
    region: string

database:
  type: enum[sqlite, postgresql]
  url: string
  pool_size: integer
  max_overflow: integer

cache:
  type: enum[redis, memcached]
  url: string
  ttl: integer

search:
  vector:
    provider: enum[qdrant, weaviate, pinecone]
    url: string
  graph:
    provider: enum[neo4j, arangodb]
    url: string
  fulltext:
    provider: enum[elasticsearch, opensearch]
    url: string

llm:
  providers:
    openai:
      api_key: string
      model: string
    anthropic:
      api_key: string
      model: string

telemetry:
  enabled: boolean
  service_name: string
  otlp_endpoint: string
  sampling_rate: float
```

### B. API Endpoint Summary
```
Documents:
  POST   /api/documents              - Create document
  GET    /api/documents              - List documents
  GET    /api/documents/{id}         - Get document
  PUT    /api/documents/{id}         - Update document
  DELETE /api/documents/{id}         - Delete document
  POST   /api/documents/upload       - Upload file
  GET    /api/documents/{id}/versions- Get versions

Processing:
  POST   /api/process/pdf-to-markdown- Convert PDF
  POST   /api/process/transcribe     - Transcribe media
  POST   /api/process/scrape         - Scrape webpage
  POST   /api/process/summarize      - Generate summary

Tools:
  GET    /api/tools                  - List tools
  POST   /api/tools/register         - Register tool
  POST   /api/tools/{id}/execute     - Execute tool

Search:
  POST   /api/search/vector          - Vector search
  POST   /api/search/graph           - Graph search
  POST   /api/search/fulltext        - Fulltext search

System:
  GET    /health                     - Health check
  GET    /metrics                    - Prometheus metrics
  GET    /api/docs                   - OpenAPI docs
```

### C. Error Codes
```python
# Standard error codes
class ErrorCode(Enum):
    DOCUMENT_NOT_FOUND = "DOC001"
    PROCESSING_FAILED = "PRO001"
    INVALID_FORMAT = "VAL001"
    UNAUTHORIZED = "AUTH001"
    RATE_LIMITED = "RATE001"
    EXTERNAL_SERVICE = "EXT001"
    INTERNAL_ERROR = "INT001"
```

---
*Last Updated: September 13, 2025*
*Version: 1.0.0*
*Authors: Mavn Bench Architecture Team*
