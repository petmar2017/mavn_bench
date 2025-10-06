"""Tests for BaseTool and tool metadata"""

from typing import Any, Dict, Optional

import pytest

from src.tools.base_tool import (BaseTool, ToolCapability, ToolCategory,
                                 ToolExecutionContext, ToolMetadata, ToolType)


class TestTool(BaseTool):
    """Test tool implementation"""

    async def execute(
        self, input_data: Dict[str, Any], context: Optional[ToolExecutionContext] = None
    ) -> Dict[str, Any]:
        return {"result": "test", "input": input_data}

    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            id="test_tool",
            name="Test Tool",
            description="Test tool for testing",
            version="1.0.0",
            category=ToolCategory.COMPUTATION,
            capabilities=[ToolCapability.TEXT_ANALYSIS],
            tool_type=ToolType.EXECUTABLE,
            input_schema={"text": {"type": "str", "required": True}},
            output_schema={"result": {"type": "str"}},
        )


@pytest.mark.asyncio
async def test_base_tool_creation():
    """Test creating a tool without dependencies"""
    tool = TestTool("test_tool")

    assert tool.name == "test_tool"
    assert tool.llm_service is None
    assert tool.document_service is None
    assert tool.vector_search_service is None


@pytest.mark.asyncio
async def test_base_tool_with_dependencies():
    """Test creating a tool with injected dependencies"""
    mock_llm = {"type": "mock_llm"}
    mock_doc = {"type": "mock_doc"}

    tool = TestTool("test_tool", llm_service=mock_llm, document_service=mock_doc)

    assert tool.llm_service == mock_llm
    assert tool.document_service == mock_doc


@pytest.mark.asyncio
async def test_base_tool_execute():
    """Test tool execution"""
    tool = TestTool("test_tool")

    result = await tool.execute({"text": "hello"})

    assert result["result"] == "test"
    assert result["input"]["text"] == "hello"


@pytest.mark.asyncio
async def test_base_tool_execute_with_context():
    """Test tool execution with context"""
    tool = TestTool("test_tool")
    context = ToolExecutionContext(
        user_id="user_123", session_id="session_456", trace_id="trace_789"
    )

    result = await tool.execute({"text": "hello"}, context)

    assert result["result"] == "test"


def test_base_tool_get_metadata():
    """Test getting tool metadata"""
    tool = TestTool("test_tool")
    metadata = tool.get_metadata()

    assert metadata.id == "test_tool"
    assert metadata.name == "Test Tool"
    assert metadata.category == ToolCategory.COMPUTATION
    assert ToolCapability.TEXT_ANALYSIS in metadata.capabilities
    assert metadata.tool_type == ToolType.EXECUTABLE


def test_base_tool_validate_input_valid():
    """Test input validation with valid input"""
    tool = TestTool("test_tool")

    # Valid input matching schema
    result = tool.validate_input({"text": "hello"})
    assert result is True


def test_base_tool_validate_input_missing_required():
    """Test input validation with missing required field"""
    tool = TestTool("test_tool")

    # Missing required 'text' field
    with pytest.raises(ValueError, match="Required field 'text' missing"):
        tool.validate_input({})


def test_base_tool_validate_input_wrong_type():
    """Test input validation with wrong type"""
    tool = TestTool("test_tool")

    # Wrong type for 'text' (should be str, not int)
    with pytest.raises(ValueError, match="Field 'text' must be str"):
        tool.validate_input({"text": 123})


def test_tool_execution_context():
    """Test tool execution context"""
    context = ToolExecutionContext(
        user_id="user_123",
        session_id="session_456",
        trace_id="trace_789",
        metadata={"custom": "data"},
    )

    assert context.user_id == "user_123"
    assert context.session_id == "session_456"
    assert context.trace_id == "trace_789"
    assert context.metadata["custom"] == "data"
    assert context.timestamp is not None


def test_tool_metadata_full():
    """Test tool metadata with all fields"""
    metadata = ToolMetadata(
        id="test_tool",
        name="Test Tool",
        description="Test description",
        version="1.0.0",
        author="Test Author",
        category=ToolCategory.LLM,
        capabilities=[ToolCapability.TEXT_GENERATION, ToolCapability.SUMMARIZATION],
        tool_type=ToolType.LLM,
        input_schema={"text": {"type": "str", "required": True}},
        output_schema={"result": {"type": "str"}},
        requires_llm=True,
        requires_mcp=False,
        requires_vector_db=True,
        execution_time_estimate="medium",
        max_input_length=1000,
        supports_streaming=True,
        is_async=True,
        examples=[{"input": {"text": "test"}, "output": {"result": "test"}}],
        documentation_url="https://example.com/docs",
    )

    assert metadata.id == "test_tool"
    assert metadata.category == ToolCategory.LLM
    assert len(metadata.capabilities) == 2
    assert metadata.requires_llm is True
    assert metadata.requires_vector_db is True
    assert metadata.supports_streaming is True
    assert len(metadata.examples) == 1


def test_tool_metadata_minimal():
    """Test tool metadata with minimal fields"""
    metadata = ToolMetadata(
        id="minimal_tool",
        name="Minimal Tool",
        description="Minimal description",
        category=ToolCategory.COMPUTATION,
        tool_type=ToolType.EXECUTABLE,
    )

    assert metadata.id == "minimal_tool"
    assert metadata.capabilities == []
    assert metadata.requires_llm is False
    assert metadata.examples == []
