# Mavn Bench Documentation Index

## Quick Start for Claude Code

### 🚀 Start Here
1. Read `claude.md` in project root - Contains ALL project-specific guidelines
2. Activate venv: `cd backend && source venv/bin/activate`
3. Current Phase: **Phase 2 - Storage Layer**
4. Next Task: Complete `backend/src/storage/filesystem_storage.py`

## 📚 Documentation Structure

### Essential Guidelines
- **[claude.md](../claude.md)** - 🎯 **START HERE** - Complete project guidelines for Claude Code
- **[prompt.md](../prompt.md)** - General development methodology (reference)

### Architecture & Design
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Complete system architecture (1025 lines)
  - System components and interactions
  - Design patterns (Factory, Service, Adapter)
  - Technology stack decisions
  - Security and scalability

### Implementation Guides
- **[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)** - Detailed 10-phase plan (514 lines)
  - Phase checklists
  - File structure
  - Timeline estimates
  - Success criteria

- **[SERVICE_IMPLEMENTATION_GUIDE.md](SERVICE_IMPLEMENTATION_GUIDE.md)** - Code templates (846 lines)
  - Complete service examples
  - Testing templates
  - Common patterns
  - Debugging tips

## 🎯 Current Implementation Status

### ✅ Phase 1: Core Infrastructure (COMPLETED)
- Configuration management
- Centralized logging
- OpenTelemetry setup
- Base service class
- Document models

### 🚧 Phase 2: Storage Layer (CURRENT)
**Files to implement:**
```bash
backend/src/storage/storage_factory.py      # Create factory
backend/src/storage/filesystem_storage.py   # Complete implementation
backend/src/storage/redis_storage.py        # Implement Redis adapter
backend/tests/unit/test_storage/           # Write all tests
```

### ⏳ Phase 3: Service Layer (NEXT)
1. Service Factory
2. Document Service
3. PDF Service
4. Transcription Service
5. Web Scraping Service
6. LLM Service
7. Search Services
8. MCP Services

## 🔑 Key Patterns to Follow

### Service Creation
```python
# ALWAYS use factory
service = ServiceFactory.create(ServiceType.PDF)
result = await service.pdf_to_markdown(file_path)
```

### Storage Access
```python
# ALWAYS use adapter
storage = StorageFactory.create(StorageType.FILESYSTEM)
await storage.save(doc_id, content)
```

### Error Handling
```python
# ALWAYS detailed errors
with self.traced_operation("operation", **attributes):
    try:
        # operation
    except SpecificError as e:
        self.logger.error(f"Specific error: {e}")
        raise
    except Exception as e:
        self.logger.error(f"Unexpected: {e}")
        raise OperationError() from e
```

## 📋 Quick Checklist

### Before Starting Any Work
- [ ] Read `claude.md` completely
- [ ] Activate venv: `source backend/venv/bin/activate`
- [ ] Verify Python 3.13+: `python --version`
- [ ] Check current phase in this document

### While Coding
- [ ] Using async/await for ALL I/O
- [ ] Adding type hints to EVERY function
- [ ] Following factory/service patterns
- [ ] Including comprehensive error handling
- [ ] Adding OpenTelemetry tracing
- [ ] Writing real tests (NO MOCKS)

### After Each Component
- [ ] Run tests: `pytest tests/ -v --cov=src`
- [ ] Check coverage >= 80%
- [ ] Format: `black src/ tests/`
- [ ] Commit with detailed message
- [ ] Push to GitHub

## 🛠️ Development Commands

```bash
# Setup and activation
cd /Users/petermager/Downloads/code/mavn_bench/backend
source venv/bin/activate

# Testing
pytest tests/unit/test_storage/ -v --cov=src/storage
pytest --cov=src --cov-report=html

# Code quality
black src/ tests/
isort src/ tests/

# Run backend
make dev-backend

# See all commands
make help
```

## 📊 Requirements Summary

- **Python**: 3.13+ (MUST use venv)
- **Test Coverage**: >= 80%
- **Response Time**: < 200ms (p95)
- **Async**: ALL I/O operations
- **Patterns**: Factory, Service, Adapter
- **Testing**: Real implementations only (NO MOCKS)
- **Documentation**: Update with each change

## 🔗 Important Links

- **GitHub**: https://github.com/petmar2017/mavn_bench
- **Project Root**: `/Users/petermager/Downloads/code/mavn_bench`
- **Backend**: `/Users/petermager/Downloads/code/mavn_bench/backend`

## ⚠️ Critical Rules

1. **NEVER** use mock objects in tests
2. **NEVER** use synchronous I/O in async functions
3. **ALWAYS** use venv
4. **ALWAYS** follow factory/service patterns
5. **ALWAYS** achieve 80%+ test coverage

---
**Last Updated**: September 13, 2025  
**Current Phase**: Phase 2 - Storage Layer  
**Next Action**: Complete FilesystemStorage and tests
