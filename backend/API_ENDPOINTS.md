# Mavn Bench API Endpoints

The API server is running at http://localhost:8000

## API Documentation
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc
- OpenAPI Schema: http://localhost:8000/api/openapi.json

## Available Services (Registered)
- DocumentService - Document CRUD operations
- PDFService - PDF to Markdown conversion
- TranscriptionService - Media transcription
- WebScrapingService - Web page to Markdown
- LLMService - AI operations (summary, entities, Q&A)
- VectorSearchService - Qdrant-based similarity search

## Endpoints

### System
- `GET /` - API status
- `GET /api/health` - Health check with service status
- `GET /api/info` - API information and features

### Document Management
- `POST /api/documents` - Create document
- `GET /api/documents` - List documents
- `GET /api/documents/{id}` - Get document
- `PUT /api/documents/{id}` - Update document
- `DELETE /api/documents/{id}` - Delete document
- `POST /api/documents/upload` - Upload file
- `GET /api/documents/{id}/versions` - Get versions

### Processing
- `POST /api/process/pdf-to-markdown` - Convert PDF to Markdown
- `POST /api/process/transcribe` - Transcribe audio/video
- `POST /api/process/scrape` - Scrape webpage to Markdown
- `POST /api/process/summarize` - Generate document summary
- `POST /api/process/extract-entities` - Extract entities
- `POST /api/process/classify` - Classify document
- `POST /api/process/batch` - Batch process documents

### Search
- `POST /api/search/vector` - Vector similarity search
- `POST /api/search/similar` - Find similar documents
- `POST /api/search/fulltext` - Full-text search (mock)
- `POST /api/search/graph` - Graph-based search (mock)
- `POST /api/search/hybrid` - Hybrid search combining strategies
- `POST /api/search/index/{document_id}` - Index document for search
- `DELETE /api/search/index/{document_id}` - Remove from index

### WebSocket
- `GET /api/ws/connections` - List active connections
- WebSocket endpoint at `/api/ws/{client_id}`

## Example Usage

### Create a Document
```bash
curl -X POST http://localhost:8000/api/documents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Document",
    "document_type": "pdf",
    "content": "Document content here"
  }'
```

### Convert PDF to Markdown
```bash
curl -X POST http://localhost:8000/api/process/pdf-to-markdown \
  -F "file=@document.pdf"
```

### Vector Search
```bash
curl -X POST http://localhost:8000/api/search/vector \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning algorithms",
    "limit": 10,
    "threshold": 0.7
  }'
```

## Authentication
Currently using mock authentication. In production, implement proper JWT/OAuth2.

## Next Steps for Frontend Integration

The API is now ready for React frontend integration. All core services are exposed via REST endpoints with:

1. **Document Management** - Full CRUD operations
2. **File Processing** - PDF, transcription, web scraping
3. **AI Operations** - Summarization, entity extraction, classification
4. **Search Capabilities** - Vector search with Qdrant
5. **Real-time Updates** - WebSocket support for live updates

The frontend can now:
- Upload and manage documents
- Process various file types
- Search documents using semantic similarity
- Get real-time updates via WebSocket
- Access all services through a unified API