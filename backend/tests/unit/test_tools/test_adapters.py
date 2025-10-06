"""Tests for tool adapters"""

import json
import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.tools.adapters.executable_tool_adapter import ExecutableToolAdapter
from src.tools.adapters.mcp_tool_adapter import MCPToolAdapter
from src.tools.base_tool import (ToolCapability, ToolCategory,
                                 ToolExecutionContext, ToolType)


@pytest.mark.asyncio
async def test_mcp_tool_adapter_basic_execution():
    """Test basic MCP tool execution"""
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = Mock()
        mock_response.json.return_value = {"result": "success", "data": "test"}
        mock_response.raise_for_status = Mock()

        mock_post = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.post = mock_post

        adapter = MCPToolAdapter(
            name="test_mcp_tool",
            mcp_server_url="http://localhost:8000",
            mcp_tool_name="test_tool",
            description="Test MCP tool",
            category=ToolCategory.COMPUTATION,
            input_schema={"query": {"type": "str", "required": True}},
        )

        result = await adapter.execute({"query": "test query"})

        assert result == {"result": "success", "data": "test"}
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:8000/execute"
        assert call_args[1]["json"]["tool"] == "test_tool"
        assert call_args[1]["json"]["parameters"] == {"query": "test query"}


@pytest.mark.asyncio
async def test_mcp_tool_adapter_with_context():
    """Test MCP tool execution with context"""
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = Mock()
        mock_response.json.return_value = {"result": "success"}
        mock_response.raise_for_status = Mock()

        mock_post = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.post = mock_post

        adapter = MCPToolAdapter(
            name="test_tool",
            mcp_server_url="http://localhost:8000",
            mcp_tool_name="test",
        )

        context = ToolExecutionContext(
            user_id="user_123", session_id="session_456", trace_id="trace_789"
        )

        await adapter.execute({"input": "test"}, context)

        call_args = mock_post.call_args
        request_data = call_args[1]["json"]
        assert request_data["context"]["user_id"] == "user_123"
        assert request_data["context"]["session_id"] == "session_456"
        assert request_data["context"]["trace_id"] == "trace_789"


@pytest.mark.asyncio
async def test_mcp_tool_adapter_http_error():
    """Test MCP tool HTTP error handling"""
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("HTTP 500 Error")

        mock_post = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.post = mock_post

        adapter = MCPToolAdapter(
            name="test_tool",
            mcp_server_url="http://localhost:8000",
            mcp_tool_name="test",
        )

        with pytest.raises(Exception, match="HTTP 500 Error"):
            await adapter.execute({"input": "test"})


def test_mcp_tool_metadata():
    """Test MCP tool metadata"""
    adapter = MCPToolAdapter(
        name="mcp_test",
        mcp_server_url="http://localhost:8000",
        mcp_tool_name="test_tool",
        description="Test MCP Tool",
        category=ToolCategory.COMMUNICATION,
        capabilities=[ToolCapability.DATA_EXTRACTION],
        input_schema={"text": {"type": "str", "required": True}},
        output_schema={"result": {"type": "str"}},
    )

    metadata = adapter.get_metadata()

    assert metadata.id == "mcp_test"
    assert metadata.name == "mcp_test"
    assert metadata.description == "Test MCP Tool"
    assert metadata.category == ToolCategory.COMMUNICATION
    assert metadata.tool_type == ToolType.MCP
    assert ToolCapability.DATA_EXTRACTION in metadata.capabilities
    assert metadata.input_schema == {"text": {"type": "str", "required": True}}


@pytest.mark.asyncio
async def test_executable_tool_adapter_python_script(tmp_path):
    """Test executable tool adapter with Python script"""
    # Create a test Python script
    script_path = tmp_path / "test_script.py"
    script_content = """
import sys
import json

data = json.loads(sys.stdin.read())
result = {
    "output": data["input"]["text"].upper(),
    "length": len(data["input"]["text"])
}
print(json.dumps(result))
"""
    script_path.write_text(script_content)

    adapter = ExecutableToolAdapter(
        name="python_tool",
        executable_path=str(script_path),
        executable_type="python",
        description="Test Python tool",
        category=ToolCategory.TRANSFORMATION,
        input_schema={"text": {"type": "str", "required": True}},
    )

    result = await adapter.execute({"text": "hello world"})

    assert result["output"] == "HELLO WORLD"
    assert result["length"] == 11


@pytest.mark.asyncio
async def test_executable_tool_adapter_with_context(tmp_path):
    """Test executable tool with execution context"""
    script_path = tmp_path / "test_context.py"
    script_content = """
import sys
import json

data = json.loads(sys.stdin.read())
result = {
    "trace_id": data.get("context", {}).get("trace_id"),
    "user_id": data.get("context", {}).get("user_id")
}
print(json.dumps(result))
"""
    script_path.write_text(script_content)

    adapter = ExecutableToolAdapter(
        name="context_tool", executable_path=str(script_path), executable_type="python"
    )

    context = ToolExecutionContext(
        user_id="user_123", session_id="session_456", trace_id="trace_789"
    )

    result = await adapter.execute({"input": "test"}, context)

    assert result["trace_id"] == "trace_789"
    assert result["user_id"] == "user_123"


@pytest.mark.asyncio
async def test_executable_tool_adapter_script_error(tmp_path):
    """Test executable tool script error handling"""
    script_path = tmp_path / "error_script.py"
    script_content = """
import sys
sys.exit(1)  # Exit with error
"""
    script_path.write_text(script_content)

    adapter = ExecutableToolAdapter(
        name="error_tool", executable_path=str(script_path), executable_type="python"
    )

    with pytest.raises(RuntimeError, match="Execution failed"):
        await adapter.execute({"input": "test"})


@pytest.mark.asyncio
async def test_executable_tool_adapter_timeout(tmp_path):
    """Test executable tool timeout"""
    script_path = tmp_path / "slow_script.py"
    script_content = """
import time
time.sleep(10)
"""
    script_path.write_text(script_content)

    adapter = ExecutableToolAdapter(
        name="slow_tool",
        executable_path=str(script_path),
        executable_type="python",
        timeout=1,  # 1 second timeout
    )

    with pytest.raises(Exception):  # asyncio.TimeoutError
        await adapter.execute({"input": "test"})


def test_executable_tool_invalid_path():
    """Test executable tool with invalid path"""
    with pytest.raises(ValueError, match="Executable not found"):
        ExecutableToolAdapter(
            name="invalid_tool",
            executable_path="/nonexistent/script.py",
            executable_type="python",
        )


def test_executable_tool_metadata():
    """Test executable tool metadata"""
    # Create a temporary valid file for initialization
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
        temp_path = f.name

    try:
        adapter = ExecutableToolAdapter(
            name="exec_test",
            executable_path=temp_path,
            executable_type="python",
            description="Test Executable Tool",
            category=ToolCategory.COMPUTATION,
            capabilities=[ToolCapability.DATA_EXTRACTION],
            input_schema={"data": {"type": "str", "required": True}},
            output_schema={"result": {"type": "dict"}},
        )

        metadata = adapter.get_metadata()

        assert metadata.id == "exec_test"
        assert metadata.name == "exec_test"
        assert metadata.description == "Test Executable Tool"
        assert metadata.category == ToolCategory.COMPUTATION
        assert metadata.tool_type == ToolType.EXECUTABLE
        assert ToolCapability.DATA_EXTRACTION in metadata.capabilities
    finally:
        Path(temp_path).unlink()


@pytest.mark.asyncio
async def test_executable_tool_binary_mode(tmp_path):
    """Test executable tool with binary executable"""
    # Create a simple shell script
    script_path = tmp_path / "test_script.sh"
    script_content = """#!/bin/bash
read input
echo '{"result": "processed"}'
"""
    script_path.write_text(script_content)
    script_path.chmod(0o755)

    adapter = ExecutableToolAdapter(
        name="binary_tool",
        executable_path=str(script_path),
        executable_type="binary",
        description="Test binary tool",
    )

    result = await adapter.execute({"input": "test"})

    assert "result" in result
