# Development Guidelines & Requirements

## How to use: if you ask to select the relevant itmes for certain prompt request then you have to dipslay them them to the user before you action them.

Development Methodology

- **Bottom-up Development**
  - Stay focused and build bottom-up building blocks
  - Assume logic sits in server-side service unless told otherwise
  - After every milestone run end-to-end tests and fix all issues
  - As you build major components enhance the tests, re-run all tests and fix all issues
  - Only move to next level implementation if all tests are working
  - NO MOCK functions, only fully working functions, code or classes
  - Use Python 3.13.x, latest Node.js and latest React libraries when possible
  - always use the venv if it is available

## Testing Requirements

### Test-Driven Development (TDD)

- **Python Backend**

  - Unit tests using pytest for all services
  - Integration tests for API endpoints
  - Test coverage minimum 80%
- **React Frontend**

  - Jest tests with strict TypeScript testing
  - Same testing level as React core uses
  - Component testing with React Testing Library
- **General Testing Rules**

  - Create and maintain comprehensive test cases continuously
  - Absolutely NO MOCK tests - always test real functions with real data and links
  - End-to-end testing after each major feature
  - OpenTelemetry trace validation in tests

## Documentation

- Continuously maintain `CHANGELOG.md`
- Build library of documents in `./docs` directory for each major component
- Maintain documentation throughout the development process
- Document OpenTelemetry trace flows and service dependencies

## Git & CI/CD

- **Commit Standards**

  - Comprehensive commit messages describing changes in detail
  - Use Git log to identify changes and comment on them
  - Push changes frequently
- **CI/CD Pipeline**

  - Configure git workflows for CI/CD readiness
  - Automated testing on pull requests
  - OpenTelemetry trace validation in CI pipeline

## OpenTelemetry & Observability

### Core Requirements

- **W3C Trace Context Standard**

  - Use industry standard format: trace_id (32 hex chars), span_id (16 hex chars)
  - Implement W3C Trace Context propagation between all services
  - Include traceparent header in all HTTP requests
- **Instrumentation Requirements**

  - Auto-instrument HTTP clients (requests, httpx, fetch, XHR)
  - Auto-instrument databases (SQLAlchemy, Redis, MongoDB)
  - Auto-instrument frameworks (FastAPI, Flask, Express)
  - Manual instrumentation for business operations

### Python Backend Implementation

```python
# Every service must inherit from BaseService
class BaseService:
    def __init__(self, service_name: str):
        self.tracer = trace.get_tracer(service_name)
        self.logger = CentralizedLogger(service_name)
  
    @contextmanager
    def traced_operation(self, operation_name: str, **attributes):
        # Automatic tracing + logging + error handling
```

- **Service Requirements**

  - All services must use BaseService pattern with automatic tracing
  - Every public method must create a span
  - Include operation attributes (user_id, resource_id, etc.)
  - Propagate trace context to external services
- **Error Handling**

  - Record exceptions in spans with `span.record_exception()`
  - Set span status to ERROR on failures
  - Include stack traces in span events

### React Frontend Implementation

```typescript
// Central logger with trace context
class CentralLogger {
  log(level, message, metadata) {
    const { traceId, spanId } = getCurrentTraceContext();
    // Include trace context in all logs
  }
}
```

- **Frontend Requirements**
  - Initialize OpenTelemetry SDK on app start
  - Use `useTraced` hook for component lifecycle tracing
  - Wrap all API calls with spans
  - Include ErrorBoundary with trace context logging
  - Batch client logs with trace context to backend

### Infrastructure Requirements

- **OpenTelemetry Collector**

  - Deploy collector as sidecar or standalone service
  - Configure OTLP receivers for traces, metrics, logs
  - Export to multiple backends (Jaeger, Prometheus, Elasticsearch)
- **Monitoring Stack**

  - Jaeger for distributed tracing visualization
  - Prometheus + Grafana for metrics
  - Elasticsearch + Kibana for centralized logs
  - All searchable by trace_id

## Directory Structure

```
project/
├── docs/                 # All documentation
├── scripts/             # All scripts MUST be here
├── src/
│   ├── api/            # FastAPI application
│   ├── services/       # Service layer with tracing
│   ├── core/           # Core utilities (telemetry, logger)
│   └── models/         # Data models
├── frontend/
│   ├── src/
│   │   ├── telemetry/ # OpenTelemetry setup
│   │   ├── hooks/     # useTraced and other hooks
│   │   └── services/  # API clients with tracing
└── infrastructure/     # Docker, K8s configs
```

## Coding Design Patterns

### Central Configuration

- Single source of truth for all configuration
- Environment-based config (dev, staging, prod)
- OpenTelemetry config in central location

### Central Logging with Trace Context

```python
# Python logger must include trace context
logger.info("Operation completed", 
    trace_id=trace_id,
    span_id=span_id,
    user_id=user_id,
    session_id=session_id
)
```

- **Logger Requirements**
  - Human-readable console output with trace_id
  - JSON formatted logs for observability platforms
  - Automatic trace context injection
  - Client logs forwarded to server with full context
  - All timestamps in UTC

### Service Pattern with Tracing

```python
class UserService(BaseService):
    async def get_user(self, user_id: str, api_key: str, session_id: str):
        with self.traced_operation("get_user", 
                                  user_id=user_id,
                                  session_id=session_id):
            # Service logic here
            return user
```

- **Service Requirements**
  - All services require: api_key, user_id, session_id
  - Test mode: use `test_api_key_123456` and `test_user`
  - Anonymous mode: use "anonymous" for users without API key
  - Every service method creates a span
  - Trace context propagated to all downstream services

### Performance Patterns & Async Requirements

#### Critical: Non-Blocking Operations

- **ALL I/O operations MUST be async** to prevent blocking the event loop:
  - File I/O: Use `aiofiles` instead of synchronous `open()`
  - HTTP requests: Use `httpx.AsyncClient` or `aiohttp` instead of `requests`
  - Database: Use async drivers (asyncpg, motor, aioredis)
  - LLM APIs: Use `anthropic.AsyncAnthropic` and async OpenAI clients

#### Async Implementation Rules

```python
# ❌ BLOCKING - Never do this in async context:
with open('file.txt') as f:
    data = f.read()
response = requests.get(url)
llm_response = anthropic.Anthropic().messages.create(...)

# ✅ NON-BLOCKING - Always use async alternatives:
import aiofiles
async with aiofiles.open('file.txt') as f:
    data = await f.read()
async with httpx.AsyncClient() as client:
    response = await client.get(url)
llm_response = await anthropic.AsyncAnthropic().messages.create(...)
```

#### Service Architecture Patterns

- Avoid global instance pattern to prevent bottlenecks
- Use dependency injection for services
- Connection pooling for databases and HTTP clients
- Async/await for ALL I/O operations (file, network, database)
- Use async context managers for resource management
- Implement proper async cleanup in finally blocks

#### Concurrency Best Practices

- Run CPU-intensive tasks in thread pool: `await asyncio.to_thread(cpu_task)`
- Use `asyncio.gather()` for parallel async operations
- Implement request queuing for rate-limited APIs
- Set appropriate timeouts on all async operations
- Use background tasks for long-running operations

#### Production Server Configuration

```bash
# Development (single worker, auto-reload)
uvicorn src.api.main:app --reload --port 8000

# Production (multiple workers, no reload)
uvicorn src.api.main:app --workers 4 --port 8000

# Production with Gunicorn (recommended)
gunicorn src.api.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Time Handling

- All internal processing in UTC
- Store timestamps in UTC in database
- Display in user's local time in UI
- Include timezone in OpenTelemetry span attributes

## Bug Fixing & Enhancement

- **Code Consistency**

  - Follow existing design patterns and conventions
  - Fix inconsistencies in other components proactively
  - Maintain uniform code style across codebase
- **Testing After Fixes**

  - Update unit and Jest tests after bug fixes
  - Run full test suite to ensure everything works
  - Write regression tests to prevent bug recurrence
  - Focus on end-to-end testing
  - Verify trace_id propagation still works

## Logging Requirements

### Server-Side Logging

- Central logger with human-readable console output
- Structured JSON logs for observability platforms
- Automatic trace context injection
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Include service_name in all logs

### Client-Side Logging

```typescript
// Client logs must include
{
  message: string,
  level: LogLevel,
  traceId: string,      // W3C format
  spanId: string,       // W3C format
  userId: string,
  sessionId: string,
  timestamp: string,    // ISO 8601 UTC
  url: string,
  userAgent: string
}
```

### Distributed Tracing Flow

```
React App → API Gateway → Service Layer → Database
    ↓           ↓             ↓            ↓
    All logs include same trace_id for correlation
```

## Make Commands

### Production Commands

```makefile
make stop-all            # Stop all services
make start-all           # Start all services
make health             # Health check all services
make performance-metrics # Export performance metrics
make trace-check        # Validate trace propagation
```

### Development Commands

```makefile
make build              # Build all components
make restart-backend    # Restart backend services
make restart-frontend   # Restart frontend
make test-all          # Run all tests
make test-backend      # Run backend tests only
make test-frontend     # Run frontend tests only
make test-quick        # Run quick smoke tests
make test-tracing      # Test trace propagation
make build-docker      # Build Docker images
make logs-trace        # Follow logs for specific trace_id
```

### OpenTelemetry Commands

```makefile
make otel-start        # Start OpenTelemetry Collector
make otel-status       # Check collector status
make jaeger-ui         # Open Jaeger UI
make kibana-ui         # Open Kibana UI
make trace-test        # Test trace propagation
```

## OpenTelemetry Integration Checklist

- [ ] Python backend with OpenTelemetry SDK initialized
- [ ] React frontend with OpenTelemetry Web SDK
- [ ] BaseService pattern with automatic tracing
- [ ] CentralizedLogger with trace context
- [ ] W3C Trace Context propagation
- [ ] Client logs batched to server with trace_id
- [ ] ErrorBoundary with trace logging
- [ ] useTraced hook for React components
- [ ] OpenTelemetry Collector deployed
- [ ] Jaeger for trace visualization
- [ ] Elasticsearch + Kibana for logs
- [ ] All services instrumented
- [ ] Database queries traced
- [ ] External API calls traced
- [ ] Performance metrics exported
- [ ] Trace validation in CI/CD
- [ ] Documentation updated
- [ ] End-to-end trace testing

## Example Trace Flow

```python
# 1. React Component
const span = tracer.startSpan('UserDashboard.fetchUser');
// traceId: abc123, spanId: 001

# 2. API Call with header
fetch('/api/users/123', {
  headers: { 'traceparent': '00-abc123-001-01' }
});

# 3. FastAPI receives and continues trace
@router.get("/users/{user_id}")
async def get_user(user_id: str):
    # Automatically continues with traceId: abc123

# 4. Service layer
with self.traced_operation("get_user"):
    # New span with same traceId: abc123, spanId: 002

# 5. Database query
with self.traced_operation("db_query"):
    # traceId: abc123, spanId: 003

# Result: All operations searchable by trace_id: abc123
```

## Monitoring & Alerting

- Alert on high error rates (>1% of requests)
- Alert on slow traces (>5s for API calls)
- Monitor trace completion rate
- Track orphaned spans
- Dashboard for service dependencies
- Real-time error tracking with trace context

## Security Considerations

- Don't log sensitive data (passwords, tokens)
- Sanitize PII in spans and logs
- Use sampling for high-volume services
- Implement rate limiting on log endpoints
- Secure OpenTelemetry Collector endpoints
- Rotate API keys regularly

---

*Last Updated: July 14, 2025*
*Version: 2.0.0 - Enhanced with comprehensive OpenTelemetry requirements*
