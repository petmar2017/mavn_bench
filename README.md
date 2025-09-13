# Mavn Bench - Generic Document Processing Platform

## Overview
Mavn Bench is a comprehensive document processing platform that provides a flexible, event-driven architecture for managing, analyzing, and transforming various document types. It features MCP (Model Context Protocol) tool integration, advanced search capabilities, and enterprise-grade observability with OpenTelemetry.

## Features
- 📄 **Multi-format Support**: PDF, Word, Excel, JSON, XML, Podcasts, YouTube, Web pages
- 🔧 **MCP Tool Integration**: Dynamic tool discovery and execution based on document type
- 🔍 **Advanced Search**: Vector, graph, and full-text search capabilities
- 🎯 **Event-Driven Architecture**: Reactive components with document message passing
- 🔐 **Role-Based Access Control**: Granular permissions with API key authentication
- 📊 **OpenTelemetry Integration**: Complete observability with distributed tracing
- 🏗️ **Flexible Storage**: Filesystem or Redis backend with adapter pattern
- 🧪 **Comprehensive Testing**: 80%+ coverage with real function testing

## Architecture
```
┌──────────────────────────────────────────────────────────────────┐
│                         React Frontend                            │
├────────────────┬────────────────────┬────────────────────────────┤
│ Document Store │   Bench Component  │      Tool Panel            │
│    (Left)      │     (Middle)       │       (Right)              │
├────────────────┴────────────────────┴────────────────────────────┤
│                    Event Bus (Document Messages)                  │
├───────────────────────────────────────────────────────────────────┤
│                     FastAPI Backend                               │
├──────────────┬──────────────┬──────────────┬────────────────────┤
│ Doc Service  │ Tool Registry│ Search Engine │   MCP Proxy        │
├──────────────┴──────────────┴──────────────┴────────────────────┤
│                  Storage Adapter (FS/Redis)                       │
├───────────────────────────────────────────────────────────────────┤
│               OpenTelemetry Collector & Monitoring                │
└───────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites
- Python 3.13+
- Node.js 18+
- Docker & Docker Compose
- Redis (optional)
- PostgreSQL (optional)

### Setup
```bash
# Clone the repository
git clone https://github.com/yourusername/mavn_bench.git
cd mavn_bench

# Run setup
make setup

# Start development environment
make dev
```

### Testing
```bash
# Run all tests
make test-all

# Run backend tests only
make test-backend

# Run frontend tests only
make test-frontend

# Test OpenTelemetry trace propagation
make test-tracing
```

## Development

### Technology Stack
- **Backend**: FastAPI, Python 3.13, SQLAlchemy, Pydantic
- **Frontend**: React, TypeScript, Chakra UI
- **Storage**: PostgreSQL/SQLite, Redis, Filesystem
- **Search**: Qdrant (vector), Neo4j (graph), Elasticsearch (full-text)
- **Monitoring**: OpenTelemetry, Jaeger, Prometheus, Grafana
- **Testing**: Pytest, Jest, React Testing Library

### Project Structure
```
mavn_bench/
├── backend/          # FastAPI backend application
├── frontend/         # React frontend application
├── infrastructure/   # Docker, Kubernetes configs
├── scripts/          # Utility scripts
├── docs/            # Documentation
└── tests/           # Integration tests
```

## Configuration
All configuration is server-side driven through `config/settings.yaml`:

```yaml
app:
  name: "Mavn Bench"
  version: "1.0.0"
  
storage:
  type: "filesystem"  # or "redis"
  
auth:
  provider: "internal"  # or "entra"
```

## Contributing
Please see [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

## License
MIT License - see [LICENSE](LICENSE) file for details.

## Status
🚧 **Active Development** - v1.0.0 in progress

---
Built with ❤️ following enterprise development standards and OpenTelemetry best practices.
