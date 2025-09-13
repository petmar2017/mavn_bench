# Service Implementation Guide for Claude Code

## Quick Start for Implementation

### Prerequisites
```bash
cd /Users/petermager/Downloads/code/mavn_bench/backend
source venv/bin/activate  # ALWAYS use venv
python --version  # Ensure Python 3.13+
```

## Service Pattern Template

### 1. Base Service Implementation (ALREADY DONE ✅)
Location: `backend/src/services/base_service.py`

### 2. Create Service Factory
```python
# backend/src/services/service_factory.py
"""Service factory for creating service instances"""

from typing import Type, Dict, Any
from enum import Enum
from .base_service import BaseService
from ..core.logger import CentralizedLogger

class ServiceType(str, Enum):
    DOCUMENT = "document"
    PDF = "pdf"
    TRANSCRIPTION = "transcription"
    WEB_SCRAPING = "web_scraping"
    LLM = "llm"
    VECTOR_SEARCH = "vector_search"
    GRAPH_SEARCH = "graph_search"
    FULLTEXT_SEARCH = "fulltext_search"
    MCP_REGISTRY = "mcp_registry"
    MCP_PROXY = "mcp_proxy"

class ServiceFactory:
    """Factory for creating service instances with dependency injection"""
    
    _services: Dict[ServiceType, Type[BaseService]] = {}
    _instances: Dict[ServiceType, BaseService] = {}
    _logger = CentralizedLogger("ServiceFactory")
    
    @classmethod
    def register(cls, service_type: ServiceType, service_class: Type[BaseService]):
        """Register a service class"""
        cls._services[service_type] = service_class
        cls._logger.info(f"Registered service: {service_type}")
    
    @classmethod
    def create(cls, service_type: ServiceType, **kwargs) -> BaseService:
        """Create or get singleton service instance"""
        # Check for existing instance (singleton pattern)
        if service_type in cls._instances:
            return cls._instances[service_type]
        
        # Create new instance
        service_class = cls._services.get(service_type)
        if not service_class:
            raise ValueError(f"Unknown service type: {service_type}")
        
        instance = service_class(**kwargs)
        cls._instances[service_type] = instance
        cls._logger.info(f"Created service instance: {service_type}")
        
        return instance
    
    @classmethod
    def clear_instances(cls):
        """Clear all singleton instances (for testing)"""
        cls._instances.clear()
```

### 3. PDF Service Implementation Example
```python
# backend/src/services/pdf_service.py
"""PDF processing service with markdown conversion"""

import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path
import aiofiles
import fitz  # PyMuPDF
import pandas as pd
from markdown import markdown

from .base_service import BaseService
from .service_factory import ServiceFactory, ServiceType
from ..models.document import DocumentMessage, DocumentContent

class PDFService(BaseService):
    """Service for PDF processing and conversion"""
    
    def __init__(self):
        super().__init__("PDFService")
        self.supported_formats = [".pdf"]
    
    async def pdf_to_markdown(self, file_path: str) -> str:
        """
        Convert PDF to markdown format
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Markdown formatted content
        """
        with self.traced_operation("pdf_to_markdown", file_path=file_path):
            try:
                # Validate file exists
                path = Path(file_path)
                if not path.exists():
                    raise FileNotFoundError(f"PDF file not found: {file_path}")
                
                # Extract text using PyMuPDF
                markdown_content = await self._extract_text_as_markdown(path)
                
                # Extract tables if present
                tables = await self._extract_tables(path)
                if tables:
                    markdown_content += "\n\n## Tables\n\n"
                    for i, table in enumerate(tables):
                        markdown_content += f"### Table {i+1}\n\n"
                        markdown_content += table.to_markdown()
                        markdown_content += "\n\n"
                
                self.logger.info(f"Successfully converted PDF to markdown: {file_path}")
                return markdown_content
                
            except Exception as e:
                self.logger.error(f"Failed to convert PDF: {str(e)}")
                raise
    
    async def _extract_text_as_markdown(self, path: Path) -> str:
        """Extract text from PDF and format as markdown"""
        # Run CPU-intensive PDF processing in thread pool
        return await asyncio.to_thread(self._sync_extract_text, str(path))
    
    def _sync_extract_text(self, file_path: str) -> str:
        """Synchronous PDF text extraction (runs in thread pool)"""
        doc = fitz.open(file_path)
        markdown_content = ""
        
        for page_num, page in enumerate(doc):
            # Add page header
            markdown_content += f"## Page {page_num + 1}\n\n"
            
            # Extract text blocks
            blocks = page.get_text("blocks")
            for block in blocks:
                text = block[4].strip()
                if text:
                    # Detect headers based on font size (simplified)
                    if len(text) < 50 and text.isupper():
                        markdown_content += f"### {text}\n\n"
                    else:
                        markdown_content += f"{text}\n\n"
        
        doc.close()
        return markdown_content
    
    async def _extract_tables(self, path: Path) -> List[pd.DataFrame]:
        """Extract tables from PDF"""
        # Placeholder for table extraction
        # In production, use camelot-py or tabula-py
        return []
    
    async def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract PDF metadata"""
        with self.traced_operation("extract_metadata", file_path=file_path):
            return await asyncio.to_thread(self._sync_extract_metadata, file_path)
    
    def _sync_extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Synchronous metadata extraction"""
        doc = fitz.open(file_path)
        metadata = doc.metadata
        doc.close()
        return metadata
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for PDF service"""
        return {
            "service": "PDFService",
            "status": "healthy",
            "supported_formats": self.supported_formats
        }

# Register the service
ServiceFactory.register(ServiceType.PDF, PDFService)
```

### 4. LLM Service Implementation Example
```python
# backend/src/services/llm_service.py
"""LLM integration service with multiple providers"""

import asyncio
from typing import List, Dict, Any, Optional
from enum import Enum
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from .base_service import BaseService
from .service_factory import ServiceFactory, ServiceType
from ..core.config import get_settings

class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"

class LLMService(BaseService):
    """Service for LLM operations with multiple providers"""
    
    def __init__(self):
        super().__init__("LLMService")
        self.settings = get_settings()
        self.client = httpx.AsyncClient(timeout=60.0)
        self.providers = self._init_providers()
    
    def _init_providers(self) -> Dict[LLMProvider, Any]:
        """Initialize LLM providers"""
        providers = {}
        
        # OpenAI provider
        if hasattr(self.settings, 'openai_api_key'):
            providers[LLMProvider.OPENAI] = {
                "api_key": self.settings.openai_api_key,
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-4"
            }
        
        # Anthropic provider
        if hasattr(self.settings, 'anthropic_api_key'):
            providers[LLMProvider.ANTHROPIC] = {
                "api_key": self.settings.anthropic_api_key,
                "base_url": "https://api.anthropic.com/v1",
                "model": "claude-3-opus-20240229"
            }
        
        return providers
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def generate_summary(
        self,
        text: str,
        max_length: int = 500,
        provider: LLMProvider = LLMProvider.OPENAI
    ) -> str:
        """
        Generate a summary of the provided text
        
        Args:
            text: Text to summarize
            max_length: Maximum length of summary
            provider: LLM provider to use
            
        Returns:
            Summary text
        """
        with self.traced_operation(
            "generate_summary",
            provider=provider,
            text_length=len(text),
            max_length=max_length
        ):
            if provider not in self.providers:
                raise ValueError(f"Provider {provider} not configured")
            
            provider_config = self.providers[provider]
            
            if provider == LLMProvider.OPENAI:
                return await self._openai_summarize(text, max_length, provider_config)
            elif provider == LLMProvider.ANTHROPIC:
                return await self._anthropic_summarize(text, max_length, provider_config)
            else:
                raise NotImplementedError(f"Provider {provider} not implemented")
    
    async def _openai_summarize(
        self,
        text: str,
        max_length: int,
        config: Dict[str, Any]
    ) -> str:
        """Generate summary using OpenAI"""
        prompt = f"Summarize the following text in {max_length} words or less:\n\n{text}"
        
        response = await self.client.post(
            f"{config['base_url']}/chat/completions",
            headers={"Authorization": f"Bearer {config['api_key']}"},
            json={
                "model": config["model"],
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_length * 2,  # Approximate token count
                "temperature": 0.7
            }
        )
        
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    
    async def _anthropic_summarize(
        self,
        text: str,
        max_length: int,
        config: Dict[str, Any]
    ) -> str:
        """Generate summary using Anthropic"""
        prompt = f"Summarize the following text in {max_length} words or less:\n\n{text}"
        
        response = await self.client.post(
            f"{config['base_url']}/messages",
            headers={
                "x-api-key": config["api_key"],
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": config["model"],
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_length * 2
            }
        )
        
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]
    
    async def extract_entities(self, text: str) -> List[Dict[str, str]]:
        """Extract named entities from text"""
        with self.traced_operation("extract_entities", text_length=len(text)):
            # Implementation for entity extraction
            pass
    
    async def answer_question(
        self,
        context: str,
        question: str,
        provider: LLMProvider = LLMProvider.OPENAI
    ) -> str:
        """Answer a question based on context"""
        with self.traced_operation(
            "answer_question",
            provider=provider,
            context_length=len(context)
        ):
            # Implementation for Q&A
            pass
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for LLM service"""
        return {
            "service": "LLMService",
            "status": "healthy",
            "providers": list(self.providers.keys())
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup"""
        await self.client.aclose()

# Register the service
ServiceFactory.register(ServiceType.LLM, LLMService)
```

### 5. Transcription Service Implementation
```python
# backend/src/services/transcription_service.py
"""Transcription service for audio/video content"""

import asyncio
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
import yt_dlp
import httpx

from .base_service import BaseService
from .service_factory import ServiceFactory, ServiceType
from ..models.document import DocumentMessage, DocumentMetadata, DocumentContent, DocumentType

class TranscriptionService(BaseService):
    """Service for transcribing audio and video content"""
    
    def __init__(self):
        super().__init__("TranscriptionService")
        self.whisper_api_key = None  # Set from config
        self.yt_dlp_options = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True
        }
    
    async def transcribe_youtube(self, url: str, user_id: str) -> DocumentMessage:
        """
        Download and transcribe YouTube video
        
        Args:
            url: YouTube video URL
            user_id: User ID for document ownership
            
        Returns:
            DocumentMessage with transcription
        """
        with self.traced_operation("transcribe_youtube", url=url):
            try:
                # Download audio
                audio_path = await self._download_youtube_audio(url)
                
                # Get video metadata
                metadata = await self._get_youtube_metadata(url)
                
                # Transcribe audio
                transcript = await self._transcribe_audio_file(audio_path)
                
                # Create document message
                document = DocumentMessage(
                    metadata=DocumentMetadata(
                        document_type=DocumentType.YOUTUBE,
                        name=metadata.get("title", "YouTube Video"),
                        summary=metadata.get("description", "")[:500],
                        source_url=url,
                        created_user=user_id,
                        updated_user=user_id
                    ),
                    content=DocumentContent(
                        formatted_content=self._format_transcript_as_markdown(
                            transcript,
                            metadata
                        ),
                        raw_text=transcript
                    )
                )
                
                # Cleanup temp file
                Path(audio_path).unlink(missing_ok=True)
                
                return document
                
            except Exception as e:
                self.logger.error(f"Failed to transcribe YouTube video: {str(e)}")
                raise
    
    async def _download_youtube_audio(self, url: str) -> str:
        """Download audio from YouTube video"""
        # Run in thread pool to avoid blocking
        return await asyncio.to_thread(self._sync_download_audio, url)
    
    def _sync_download_audio(self, url: str) -> str:
        """Synchronous audio download"""
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            output_path = tmp.name
        
        options = {
            **self.yt_dlp_options,
            'outtmpl': output_path.replace('.mp3', '.%(ext)s')
        }
        
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])
        
        # Return the actual output file (might have different extension)
        output_files = list(Path(output_path).parent.glob(
            f"{Path(output_path).stem}.*"
        ))
        return str(output_files[0]) if output_files else output_path
    
    async def _get_youtube_metadata(self, url: str) -> Dict[str, Any]:
        """Get YouTube video metadata"""
        return await asyncio.to_thread(self._sync_get_metadata, url)
    
    def _sync_get_metadata(self, url: str) -> Dict[str, Any]:
        """Synchronous metadata extraction"""
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get("title"),
                "description": info.get("description"),
                "duration": info.get("duration"),
                "uploader": info.get("uploader"),
                "upload_date": info.get("upload_date")
            }
    
    async def _transcribe_audio_file(self, file_path: str) -> str:
        """Transcribe audio file using Whisper API"""
        # For production, use OpenAI Whisper API
        # This is a placeholder implementation
        self.logger.info(f"Transcribing audio file: {file_path}")
        
        # Placeholder - return sample transcript
        return "This is a sample transcript. Implement Whisper API integration."
    
    def _format_transcript_as_markdown(
        self,
        transcript: str,
        metadata: Dict[str, Any]
    ) -> str:
        """Format transcript as markdown with metadata"""
        markdown = f"# {metadata.get('title', 'Transcript')}\n\n"
        markdown += f"**Uploader:** {metadata.get('uploader', 'Unknown')}\n"
        markdown += f"**Duration:** {metadata.get('duration', 0)} seconds\n\n"
        markdown += "## Transcript\n\n"
        markdown += transcript
        return markdown
    
    async def transcribe_podcast(self, url: str, user_id: str) -> DocumentMessage:
        """Transcribe podcast from URL"""
        # Similar implementation to YouTube
        pass
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for transcription service"""
        return {
            "service": "TranscriptionService",
            "status": "healthy",
            "whisper_configured": self.whisper_api_key is not None
        }

# Register the service
ServiceFactory.register(ServiceType.TRANSCRIPTION, TranscriptionService)
```

## Storage Factory Implementation

### 6. Storage Factory
```python
# backend/src/storage/storage_factory.py
"""Storage factory for creating storage adapters"""

from typing import Type, Dict, Any
from enum import Enum
from .adapter import StorageAdapter
from ..core.logger import CentralizedLogger

class StorageType(str, Enum):
    FILESYSTEM = "filesystem"
    REDIS = "redis"
    S3 = "s3"

class StorageFactory:
    """Factory for creating storage adapters"""
    
    _adapters: Dict[StorageType, Type[StorageAdapter]] = {}
    _logger = CentralizedLogger("StorageFactory")
    
    @classmethod
    def register(cls, storage_type: StorageType, adapter_class: Type[StorageAdapter]):
        """Register a storage adapter"""
        cls._adapters[storage_type] = adapter_class
        cls._logger.info(f"Registered storage adapter: {storage_type}")
    
    @classmethod
    def create(cls, storage_type: StorageType, **kwargs) -> StorageAdapter:
        """Create storage adapter instance"""
        adapter_class = cls._adapters.get(storage_type)
        if not adapter_class:
            raise ValueError(f"Unknown storage type: {storage_type}")
        
        instance = adapter_class(**kwargs)
        cls._logger.info(f"Created storage adapter: {storage_type}")
        return instance
```

## Testing Templates

### 7. Service Test Template
```python
# backend/tests/unit/test_services/test_pdf_service.py
"""Tests for PDF service"""

import pytest
import asyncio
from pathlib import Path

from src.services.pdf_service import PDFService
from src.services.service_factory import ServiceFactory, ServiceType

@pytest.fixture
async def pdf_service():
    """Create PDF service instance"""
    service = ServiceFactory.create(ServiceType.PDF)
    yield service
    # Cleanup if needed

@pytest.fixture
def sample_pdf_path(tmp_path):
    """Create a sample PDF for testing"""
    # Create actual PDF file, not mock
    pdf_path = tmp_path / "test.pdf"
    # Generate simple PDF content
    # ... actual PDF creation code ...
    return str(pdf_path)

@pytest.mark.asyncio
async def test_pdf_to_markdown(pdf_service, sample_pdf_path):
    """Test PDF to markdown conversion"""
    # Act
    result = await pdf_service.pdf_to_markdown(sample_pdf_path)
    
    # Assert
    assert result is not None
    assert isinstance(result, str)
    assert "## Page 1" in result  # Check for page markers
    assert len(result) > 0

@pytest.mark.asyncio
async def test_extract_metadata(pdf_service, sample_pdf_path):
    """Test PDF metadata extraction"""
    # Act
    metadata = await pdf_service.extract_metadata(sample_pdf_path)
    
    # Assert
    assert metadata is not None
    assert isinstance(metadata, dict)

@pytest.mark.asyncio
async def test_health_check(pdf_service):
    """Test service health check"""
    # Act
    health = await pdf_service.health_check()
    
    # Assert
    assert health["status"] == "healthy"
    assert health["service"] == "PDFService"
```

## Implementation Checklist for Claude Code

### Phase 2: Storage Layer
```bash
# 1. Create storage factory
touch backend/src/storage/storage_factory.py

# 2. Implement filesystem storage (already started)
# Complete backend/src/storage/filesystem_storage.py

# 3. Implement Redis storage
touch backend/src/storage/redis_storage.py

# 4. Create tests
touch backend/tests/unit/test_storage/test_storage_factory.py
touch backend/tests/unit/test_storage/test_filesystem_storage.py
touch backend/tests/unit/test_storage/test_redis_storage.py

# 5. Run tests
cd backend
./venv/bin/pytest tests/unit/test_storage/ -v --cov=src/storage
```

### Phase 3: Service Layer
```bash
# 1. Create service factory
touch backend/src/services/service_factory.py

# 2. Create services
touch backend/src/services/document_service.py
touch backend/src/services/pdf_service.py
touch backend/src/services/transcription_service.py
touch backend/src/services/web_scraping_service.py
touch backend/src/services/llm_service.py

# 3. Create search services
touch backend/src/services/vector_search_service.py
touch backend/src/services/graph_search_service.py
touch backend/src/services/fulltext_search_service.py

# 4. Create MCP services
touch backend/src/services/mcp_registry_service.py
touch backend/src/services/mcp_proxy_service.py

# 5. Create tests for each service
mkdir -p backend/tests/unit/test_services
touch backend/tests/unit/test_services/test_service_factory.py
# ... create test file for each service

# 6. Run tests
./venv/bin/pytest tests/unit/test_services/ -v --cov=src/services
```

## Key Implementation Rules

### 1. ALWAYS Use Async/Await
```python
# ❌ WRONG - Blocking I/O
def read_file(path):
    with open(path) as f:
        return f.read()

# ✅ CORRECT - Non-blocking I/O
async def read_file(path):
    async with aiofiles.open(path) as f:
        return await f.read()
```

### 2. CPU-Intensive Tasks in Thread Pool
```python
# ✅ CORRECT - Run CPU tasks in thread pool
async def process_heavy(data):
    return await asyncio.to_thread(sync_heavy_process, data)

def sync_heavy_process(data):
    # CPU-intensive work here
    pass
```

### 3. Proper Error Handling
```python
# ✅ CORRECT - Detailed error handling
async def process_document(doc_id: str):
    with self.traced_operation("process_document", doc_id=doc_id):
        try:
            document = await self.load_document(doc_id)
            result = await self._process(document)
            self.logger.info(f"Processed document: {doc_id}")
            return result
        except FileNotFoundError as e:
            self.logger.error(f"Document not found: {doc_id}")
            raise DocumentNotFoundError(f"Document {doc_id} not found") from e
        except Exception as e:
            self.logger.error(f"Failed to process document {doc_id}: {str(e)}")
            raise ProcessingError(f"Processing failed for {doc_id}") from e
```

### 4. Type Hints Everywhere
```python
# ✅ CORRECT - Full type hints
async def search_documents(
    query: str,
    limit: int = 10,
    offset: int = 0,
    filters: Optional[Dict[str, Any]] = None
) -> List[DocumentMessage]:
    """Search documents with full type safety"""
    pass
```

### 5. No Mock Objects in Tests
```python
# ❌ WRONG - Using mocks
def test_service():
    mock_storage = Mock()
    mock_storage.load.return_value = {"id": "123"}

# ✅ CORRECT - Real implementations
async def test_service(tmp_path):
    storage = FilesystemStorage(str(tmp_path))
    await storage.save("123", {"id": "123"})
    result = await storage.load("123")
    assert result["id"] == "123"
```

## Common Pitfalls to Avoid

1. **Don't use synchronous I/O in async functions**
2. **Don't forget to close resources (use context managers)**
3. **Don't ignore error handling**
4. **Don't skip type hints**
5. **Don't use global state**
6. **Don't hardcode configuration values**
7. **Don't skip tests**
8. **Don't use mocks in tests**

## Running and Testing

### Development Workflow
```bash
# 1. Always activate venv
cd /Users/petermager/Downloads/code/mavn_bench/backend
source venv/bin/activate

# 2. Install new dependencies if needed
pip install <package>
pip freeze > requirements.txt

# 3. Run tests after each component
pytest tests/unit/test_services/test_pdf_service.py -v

# 4. Check coverage
pytest --cov=src --cov-report=html

# 5. Format code
black src/ tests/
isort src/ tests/

# 6. Run full test suite before commit
make test-backend
```

### Debugging Tips
```python
# Use detailed logging
self.logger.debug(f"Processing document: {doc_id}")
self.logger.info(f"Document processed successfully: {doc_id}")
self.logger.warning(f"Slow processing for document: {doc_id} ({duration}s)")
self.logger.error(f"Failed to process: {str(e)}", exc_info=True)

# Use tracing for performance
with self.traced_operation("expensive_operation", **attributes):
    # Operation here
    pass
```

## Next Steps for Claude Code

1. **Complete Storage Layer** (Phase 2)
   - Finish filesystem_storage.py
   - Implement redis_storage.py
   - Create comprehensive tests
   - Achieve 80%+ coverage

2. **Implement Core Services** (Phase 3)
   - Start with PDFService
   - Then TranscriptionService
   - Then LLMService
   - Add tests for each

3. **Build API Layer** (Phase 4)
   - Create FastAPI routers
   - Add middleware
   - Implement WebSocket support

4. **Database Layer** (Phase 5)
   - Setup SQLAlchemy models
   - Create repositories
   - Add migrations

Remember: Test after each component, no mocks, always async!

---
*This guide is specifically for Claude Code to implement the server-side components*
*Follow the patterns exactly as shown above*
