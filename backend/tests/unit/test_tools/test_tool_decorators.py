"""Tests for tool decorators and auto-discovery"""

from typing import Any, Dict, Optional

import pytest

from src.tools.base_tool import (BaseTool, ToolCapability, ToolCategory,
                                 ToolExecutionContext, ToolMetadata, ToolType)
from src.tools.tool_decorators import (clear_decorated_tools,
                                       get_decorated_tools, initialize_tools,
                                       register_tool)
from src.tools.tool_registry import ToolRegistry


@pytest.fixture(autouse=True)
def clean_registries():
    """Clean registries before each test"""
    clear_decorated_tools()
    ToolRegistry._tools.clear()
    ToolRegistry._instances.clear()
    ToolRegistry._by_category.clear()
    ToolRegistry._by_capability.clear()
    ToolRegistry._by_type.clear()
    yield
    clear_decorated_tools()
    ToolRegistry._tools.clear()
    ToolRegistry._instances.clear()
    ToolRegistry._by_category.clear()
    ToolRegistry._by_capability.clear()
    ToolRegistry._by_type.clear()


def test_register_tool_decorator():
    """Test @register_tool decorator"""

    @register_tool("test_tool")
    class TestTool(BaseTool):
        async def execute(
            self,
            input_data: Dict[str, Any],
            context: Optional[ToolExecutionContext] = None,
        ) -> Dict[str, Any]:
            return {"result": "test"}

        def get_metadata(self) -> ToolMetadata:
            return ToolMetadata(
                id="test_tool",
                name="Test Tool",
                description="Test",
                category=ToolCategory.COMPUTATION,
                tool_type=ToolType.EXECUTABLE,
            )

    decorated = get_decorated_tools()
    assert "test_tool" in decorated
    assert decorated["test_tool"] == TestTool


def test_register_tool_with_aliases():
    """Test @register_tool decorator with aliases"""

    @register_tool("main_tool", aliases=["alt1", "alt2"])
    class AliasedTool(BaseTool):
        async def execute(
            self,
            input_data: Dict[str, Any],
            context: Optional[ToolExecutionContext] = None,
        ) -> Dict[str, Any]:
            return {"result": "test"}

        def get_metadata(self) -> ToolMetadata:
            return ToolMetadata(
                id="main_tool",
                name="Aliased Tool",
                description="Test",
                category=ToolCategory.COMPUTATION,
                tool_type=ToolType.EXECUTABLE,
            )

    decorated = get_decorated_tools()
    assert "main_tool" in decorated
    assert "alt1" in decorated
    assert "alt2" in decorated
    assert decorated["main_tool"] == AliasedTool
    assert decorated["alt1"] == AliasedTool


def test_register_tool_invalid_class():
    """Test @register_tool with non-BaseTool class raises error"""

    with pytest.raises(ValueError, match="must inherit from BaseTool"):

        @register_tool("invalid_tool")
        class InvalidTool:
            pass


def test_initialize_tools():
    """Test initialize_tools registers decorated tools"""

    @register_tool("tool1")
    class Tool1(BaseTool):
        async def execute(
            self,
            input_data: Dict[str, Any],
            context: Optional[ToolExecutionContext] = None,
        ) -> Dict[str, Any]:
            return {}

        def get_metadata(self) -> ToolMetadata:
            return ToolMetadata(
                id="tool1",
                name="Tool 1",
                description="Test",
                category=ToolCategory.COMPUTATION,
                tool_type=ToolType.EXECUTABLE,
            )

    @register_tool("tool2")
    class Tool2(BaseTool):
        async def execute(
            self,
            input_data: Dict[str, Any],
            context: Optional[ToolExecutionContext] = None,
        ) -> Dict[str, Any]:
            return {}

        def get_metadata(self) -> ToolMetadata:
            return ToolMetadata(
                id="tool2",
                name="Tool 2",
                description="Test",
                category=ToolCategory.COMPUTATION,
                tool_type=ToolType.EXECUTABLE,
            )

    count = initialize_tools()

    assert count == 2
    assert ToolRegistry.is_registered("tool1")
    assert ToolRegistry.is_registered("tool2")


def test_clear_decorated_tools():
    """Test clearing decorated tools registry"""

    @register_tool("test_tool")
    class TestTool(BaseTool):
        async def execute(
            self,
            input_data: Dict[str, Any],
            context: Optional[ToolExecutionContext] = None,
        ) -> Dict[str, Any]:
            return {}

        def get_metadata(self) -> ToolMetadata:
            return ToolMetadata(
                id="test_tool",
                name="Test Tool",
                description="Test",
                category=ToolCategory.COMPUTATION,
                tool_type=ToolType.EXECUTABLE,
            )

    assert len(get_decorated_tools()) > 0

    clear_decorated_tools()

    assert len(get_decorated_tools()) == 0


def test_tool_metadata_attributes():
    """Test that decorator adds metadata attributes to class"""

    @register_tool("test_tool", aliases=["alt"])
    class TestTool(BaseTool):
        async def execute(
            self,
            input_data: Dict[str, Any],
            context: Optional[ToolExecutionContext] = None,
        ) -> Dict[str, Any]:
            return {}

        def get_metadata(self) -> ToolMetadata:
            return ToolMetadata(
                id="test_tool",
                name="Test Tool",
                description="Test",
                category=ToolCategory.COMPUTATION,
                tool_type=ToolType.EXECUTABLE,
            )

    assert hasattr(TestTool, "_tool_id")
    assert TestTool._tool_id == "test_tool"
    assert hasattr(TestTool, "_tool_aliases")
    assert "alt" in TestTool._tool_aliases


@pytest.mark.asyncio
async def test_decorated_tool_execution():
    """Test that decorated tools can be created and executed"""

    @register_tool("exec_tool")
    class ExecutableTool(BaseTool):
        async def execute(
            self,
            input_data: Dict[str, Any],
            context: Optional[ToolExecutionContext] = None,
        ) -> Dict[str, Any]:
            return {"executed": True, "input": input_data}

        def get_metadata(self) -> ToolMetadata:
            return ToolMetadata(
                id="exec_tool",
                name="Executable Tool",
                description="Test",
                category=ToolCategory.COMPUTATION,
                tool_type=ToolType.EXECUTABLE,
            )

    initialize_tools()

    tool = ToolRegistry.create("exec_tool", singleton=False)
    result = await tool.execute({"test": "data"})

    assert result["executed"] is True
    assert result["input"]["test"] == "data"
