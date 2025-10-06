"""Tests for ToolRegistry"""

from typing import Any, Dict, Optional

import pytest

from src.tools.base_tool import (BaseTool, ToolCapability, ToolCategory,
                                 ToolExecutionContext, ToolMetadata, ToolType)
from src.tools.tool_registry import ToolRegistry


class AnalysisTool(BaseTool):
    """Test analysis tool"""

    async def execute(
        self, input_data: Dict[str, Any], context: Optional[ToolExecutionContext] = None
    ) -> Dict[str, Any]:
        return {"analysis": "complete"}

    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            id="analysis_tool",
            name="Analysis Tool",
            description="Tool for analysis",
            category=ToolCategory.ANALYSIS,
            capabilities=[
                ToolCapability.TEXT_ANALYSIS,
                ToolCapability.ENTITY_RECOGNITION,
            ],
            tool_type=ToolType.EXECUTABLE,
        )


class LLMTool(BaseTool):
    """Test LLM tool"""

    async def execute(
        self, input_data: Dict[str, Any], context: Optional[ToolExecutionContext] = None
    ) -> Dict[str, Any]:
        if not self.llm_service:
            raise ValueError("LLMTool requires llm_service for execution")
        return {"llm_result": "generated"}

    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            id="llm_tool",
            name="LLM Tool",
            description="Tool using LLM",
            category=ToolCategory.LLM,
            capabilities=[ToolCapability.TEXT_GENERATION],
            tool_type=ToolType.LLM,
            requires_llm=True,
        )


@pytest.fixture(autouse=True)
def clean_registry():
    """Clean registry before each test"""
    ToolRegistry._tools.clear()
    ToolRegistry._instances.clear()
    ToolRegistry._by_category.clear()
    ToolRegistry._by_capability.clear()
    ToolRegistry._by_type.clear()
    yield
    ToolRegistry._tools.clear()
    ToolRegistry._instances.clear()
    ToolRegistry._by_category.clear()
    ToolRegistry._by_capability.clear()
    ToolRegistry._by_type.clear()


def test_register_tool():
    """Test registering a tool"""
    ToolRegistry.register("analysis_tool", AnalysisTool)

    assert "analysis_tool" in ToolRegistry._tools
    assert ToolRegistry._tools["analysis_tool"] == AnalysisTool


def test_register_tool_builds_indexes():
    """Test that registration builds proper indexes"""
    ToolRegistry.register("analysis_tool", AnalysisTool)

    # Check category index
    assert "analysis_tool" in ToolRegistry._by_category[ToolCategory.ANALYSIS]

    # Check capability index
    assert "analysis_tool" in ToolRegistry._by_capability[ToolCapability.TEXT_ANALYSIS]
    assert (
        "analysis_tool"
        in ToolRegistry._by_capability[ToolCapability.ENTITY_RECOGNITION]
    )

    # Check type index
    assert "analysis_tool" in ToolRegistry._by_type[ToolType.EXECUTABLE]


def test_create_tool_without_dependencies():
    """Test creating a tool without dependencies"""
    ToolRegistry.register("analysis_tool", AnalysisTool)

    tool = ToolRegistry.create("analysis_tool", singleton=False)

    assert isinstance(tool, AnalysisTool)
    assert tool.name == "analysis_tool"


def test_create_tool_with_dependencies():
    """Test creating a tool with injected dependencies"""
    ToolRegistry.register("llm_tool", LLMTool)

    mock_llm = {"type": "mock_llm"}
    tool = ToolRegistry.create("llm_tool", singleton=False, llm_service=mock_llm)

    assert isinstance(tool, LLMTool)
    assert tool.llm_service == mock_llm


@pytest.mark.asyncio
async def test_execute_tool_missing_required_dependency():
    """Test executing a tool without required dependency raises error"""
    ToolRegistry.register("llm_tool", LLMTool)

    tool = ToolRegistry.create("llm_tool", singleton=False)

    with pytest.raises(ValueError, match="requires llm_service"):
        await tool.execute({})


def test_create_tool_singleton():
    """Test singleton behavior"""
    ToolRegistry.register("analysis_tool", AnalysisTool)

    tool1 = ToolRegistry.create("analysis_tool", singleton=True)
    tool2 = ToolRegistry.create("analysis_tool", singleton=True)

    assert tool1 is tool2


def test_create_tool_non_singleton():
    """Test non-singleton behavior"""
    ToolRegistry.register("analysis_tool", AnalysisTool)

    tool1 = ToolRegistry.create("analysis_tool", singleton=False)
    tool2 = ToolRegistry.create("analysis_tool", singleton=False)

    assert tool1 is not tool2


def test_create_tool_not_found():
    """Test creating non-existent tool raises error"""
    with pytest.raises(ValueError, match="Unknown tool ID"):
        ToolRegistry.create("nonexistent")


def test_get_all_tools():
    """Test getting all registered tools"""
    ToolRegistry.register("analysis_tool", AnalysisTool)
    ToolRegistry.register("llm_tool", LLMTool)

    all_tools = ToolRegistry.get_all_tools()

    assert len(all_tools) == 2
    assert "analysis_tool" in all_tools
    assert "llm_tool" in all_tools


def test_get_tool_metadata():
    """Test getting tool metadata"""
    ToolRegistry.register("analysis_tool", AnalysisTool)

    metadata = ToolRegistry.get_tool_metadata("analysis_tool")

    assert metadata.id == "analysis_tool"
    assert metadata.name == "Analysis Tool"
    assert metadata.category == ToolCategory.ANALYSIS


def test_get_tool_metadata_not_found():
    """Test getting metadata for non-existent tool"""
    metadata = ToolRegistry.get_tool_metadata("nonexistent")

    assert metadata is None


def test_find_tools_by_category():
    """Test finding tools by category"""
    ToolRegistry.register("analysis_tool", AnalysisTool)
    ToolRegistry.register("llm_tool", LLMTool)

    analysis_tools = ToolRegistry.find_tools_by_criteria(category=ToolCategory.ANALYSIS)
    llm_tools = ToolRegistry.find_tools_by_criteria(category=ToolCategory.LLM)

    assert "analysis_tool" in analysis_tools
    assert "llm_tool" in llm_tools
    assert "llm_tool" not in analysis_tools


def test_find_tools_by_capability():
    """Test finding tools by capability"""
    ToolRegistry.register("analysis_tool", AnalysisTool)
    ToolRegistry.register("llm_tool", LLMTool)

    text_analysis_tools = ToolRegistry.find_tools_by_criteria(
        capabilities=[ToolCapability.TEXT_ANALYSIS]
    )
    text_gen_tools = ToolRegistry.find_tools_by_criteria(
        capabilities=[ToolCapability.TEXT_GENERATION]
    )

    assert "analysis_tool" in text_analysis_tools
    assert "llm_tool" in text_gen_tools


def test_find_tools_by_type():
    """Test finding tools by type"""
    ToolRegistry.register("analysis_tool", AnalysisTool)
    ToolRegistry.register("llm_tool", LLMTool)

    executable_tools = ToolRegistry.find_tools_by_criteria(
        tool_type=ToolType.EXECUTABLE
    )
    llm_tools = ToolRegistry.find_tools_by_criteria(tool_type=ToolType.LLM)

    assert "analysis_tool" in executable_tools
    assert "llm_tool" in llm_tools


def test_find_tools_by_requires_llm():
    """Test finding tools by LLM requirement"""
    ToolRegistry.register("analysis_tool", AnalysisTool)
    ToolRegistry.register("llm_tool", LLMTool)

    llm_required_tools = ToolRegistry.find_tools_by_criteria(requires_llm=True)
    no_llm_required_tools = ToolRegistry.find_tools_by_criteria(requires_llm=False)

    assert "llm_tool" in llm_required_tools
    assert "analysis_tool" in no_llm_required_tools


def test_find_tools_by_multiple_criteria():
    """Test finding tools by multiple criteria"""
    ToolRegistry.register("analysis_tool", AnalysisTool)
    ToolRegistry.register("llm_tool", LLMTool)

    tools = ToolRegistry.find_tools_by_criteria(
        category=ToolCategory.ANALYSIS,
        capabilities=[ToolCapability.TEXT_ANALYSIS],
        tool_type=ToolType.EXECUTABLE,
    )

    assert "analysis_tool" in tools
    assert "llm_tool" not in tools


def test_tool_exists():
    """Test checking if tool exists"""
    ToolRegistry.register("analysis_tool", AnalysisTool)

    assert ToolRegistry.is_registered("analysis_tool") is True
    assert ToolRegistry.is_registered("nonexistent") is False


def test_clear_instances():
    """Test clearing singleton instances"""
    ToolRegistry.register("analysis_tool", AnalysisTool)

    tool1 = ToolRegistry.create("analysis_tool", singleton=True)
    ToolRegistry.clear_instances()
    tool2 = ToolRegistry.create("analysis_tool", singleton=True)

    assert tool1 is not tool2
