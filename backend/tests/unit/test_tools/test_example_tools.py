"""Tests for example tool implementations"""

from typing import Any, Dict

import pytest

from src.tools.base_tool import ToolExecutionContext
from src.tools.examples.document_analyzer_tool import DocumentAnalyzerTool
from src.tools.examples.echo_tool import EchoTool
from src.tools.examples.smart_summarize_tool import SmartSummarizeTool
from src.tools.examples.word_count_tool import WordCountTool


@pytest.mark.asyncio
async def test_word_count_tool():
    """Test word count tool execution"""
    tool = WordCountTool("word_count")

    result = await tool.execute({"text": "Hello world! This is a test."})

    assert result["word_count"] == 6
    assert result["line_count"] == 1
    assert result["unique_words"] == 6
    # Character count includes the entire string
    assert result["character_count"] > 0


@pytest.mark.asyncio
async def test_word_count_tool_multiline():
    """Test word count tool with multiline text"""
    tool = WordCountTool("word_count")

    result = await tool.execute({"text": "Line 1\nLine 2\nLine 3"})

    assert result["line_count"] == 3
    assert result["word_count"] == 6


@pytest.mark.asyncio
async def test_word_count_tool_duplicate_words():
    """Test word count tool with duplicate words"""
    tool = WordCountTool("word_count")

    result = await tool.execute({"text": "hello HELLO Hello world"})

    assert result["word_count"] == 4
    assert result["unique_words"] == 2


@pytest.mark.asyncio
async def test_echo_tool():
    """Test echo tool execution"""
    tool = EchoTool("echo")

    result = await tool.execute({"message": "Test message"})

    assert result["echoed_message"] == "Test message"
    assert result["message_length"] == 12
    assert result["context_id"] is None


@pytest.mark.asyncio
async def test_echo_tool_with_context():
    """Test echo tool with execution context"""
    tool = EchoTool("echo")
    context = ToolExecutionContext(
        user_id="user_123", session_id="session_456", trace_id="trace_789"
    )

    result = await tool.execute({"message": "Test"}, context)

    assert result["context_id"] == "trace_789"


@pytest.mark.asyncio
async def test_smart_summarize_tool_requires_llm_service():
    """Test smart summarize tool requires LLM service"""
    with pytest.raises(ValueError, match="requires llm_service"):
        SmartSummarizeTool("smart_summarize")


@pytest.mark.asyncio
async def test_smart_summarize_tool_with_mock_llm():
    """Test smart summarize tool with mocked LLM service"""

    class MockLLMService:
        async def summarize(self, text: str, max_length: int = 200, trace_id=None):
            return "This is a summary"

    tool = SmartSummarizeTool("smart_summarize", llm_service=MockLLMService())

    result = await tool.execute(
        {"text": "Long text that needs summarization", "max_length": 50}
    )

    assert result["summary"] == "This is a summary"
    assert result["original_length"] == 34
    assert result["summary_length"] == 17


@pytest.mark.asyncio
async def test_document_analyzer_tool_requires_services():
    """Test document analyzer tool requires services"""
    with pytest.raises(ValueError, match="requires document_service"):
        DocumentAnalyzerTool("document_analyzer")

    with pytest.raises(ValueError, match="requires llm_service"):
        DocumentAnalyzerTool("document_analyzer", document_service={"mock": "service"})


@pytest.mark.asyncio
async def test_document_analyzer_tool_with_mock_services():
    """Test document analyzer tool with mocked services"""

    class MockMetadata:
        document_type = "pdf"

    class MockContent:
        text = "This is a test document with some content."

    class MockDocument:
        def __init__(self):
            self.metadata = MockMetadata()
            self.content = MockContent()

    class MockDocumentService:
        async def get_document(self, doc_id: str, trace_id=None):
            return MockDocument()

    class MockLLMService:
        async def summarize(self, text: str, trace_id=None):
            return "Test summary"

        async def extract_entities(self, text: str, trace_id=None):
            return ["Entity1", "Entity2"]

    tool = DocumentAnalyzerTool(
        "document_analyzer",
        document_service=MockDocumentService(),
        llm_service=MockLLMService(),
    )

    result = await tool.execute({"document_id": "doc_123"})

    assert result["document_id"] == "doc_123"
    assert result["document_type"] == "pdf"
    assert result["summary"] == "Test summary"
    assert "Entity1" in result["entities"]
    assert result["word_count"] > 0
    assert "similar_documents" not in result


@pytest.mark.asyncio
async def test_document_analyzer_tool_with_vector_search():
    """Test document analyzer tool with optional vector search"""

    class MockMetadata:
        document_type = "pdf"

    class MockContent:
        text = "Test content"

    class MockDocument:
        def __init__(self):
            self.metadata = MockMetadata()
            self.content = MockContent()

    class MockDocumentService:
        async def get_document(self, doc_id: str, trace_id=None):
            return MockDocument()

    class MockLLMService:
        async def summarize(self, text: str, trace_id=None):
            return "Summary"

        async def extract_entities(self, text: str, trace_id=None):
            return []

    class MockVectorSearchService:
        async def find_similar(self, document_id: str, limit: int = 5, trace_id=None):
            return [{"id": "doc_456"}, {"id": "doc_789"}]

    tool = DocumentAnalyzerTool(
        "document_analyzer",
        document_service=MockDocumentService(),
        llm_service=MockLLMService(),
        vector_search_service=MockVectorSearchService(),
    )

    result = await tool.execute({"document_id": "doc_123"})

    assert "similar_documents" in result
    assert len(result["similar_documents"]) == 2
    assert "doc_456" in result["similar_documents"]


def test_word_count_tool_metadata():
    """Test word count tool metadata"""
    tool = WordCountTool("word_count")
    metadata = tool.get_metadata()

    assert metadata.id == "word_count"
    assert metadata.name == "Word Counter"
    assert len(metadata.examples) > 0


def test_echo_tool_metadata():
    """Test echo tool metadata"""
    tool = EchoTool("echo")
    metadata = tool.get_metadata()

    assert metadata.id == "echo"
    assert metadata.name == "Echo Tool"


def test_smart_summarize_tool_metadata():
    """Test smart summarize tool metadata"""

    class MockLLMService:
        pass

    tool = SmartSummarizeTool("smart_summarize", llm_service=MockLLMService())
    metadata = tool.get_metadata()

    assert metadata.id == "smart_summarize"
    assert metadata.requires_llm is True


def test_document_analyzer_tool_metadata():
    """Test document analyzer tool metadata"""
    tool = DocumentAnalyzerTool(
        "document_analyzer",
        document_service={"mock": "service"},
        llm_service={"mock": "service"},
    )
    metadata = tool.get_metadata()

    assert metadata.id == "document_analyzer"
    assert metadata.requires_llm is True
