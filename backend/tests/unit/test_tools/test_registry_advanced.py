"""Advanced tests for ToolRegistry edge cases and complex scenarios"""

from typing import Any, Dict, Optional

import pytest

from src.tools.base_tool import (BaseTool, ToolCapability, ToolCategory,
                                 ToolExecutionContext, ToolMetadata, ToolType)
from src.tools.tool_registry import ToolRegistry


class ComplexTool(BaseTool):
    """Tool with multiple capabilities and dependencies"""

    async def execute(
        self, input_data: Dict[str, Any], context: Optional[ToolExecutionContext] = None
    ) -> Dict[str, Any]:
        return {"result": "complex"}

    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            id="complex_tool",
            name="Complex Tool",
            description="Tool with multiple features",
            category=ToolCategory.ANALYSIS,
            capabilities=[
                ToolCapability.TEXT_ANALYSIS,
                ToolCapability.ENTITY_RECOGNITION,
                ToolCapability.SUMMARIZATION,
            ],
            tool_type=ToolType.HYBRID,
            requires_llm=True,
            requires_vector_db=True,
        )


class MinimalTool(BaseTool):
    """Minimal tool with no optional features"""

    async def execute(
        self, input_data: Dict[str, Any], context: Optional[ToolExecutionContext] = None
    ) -> Dict[str, Any]:
        return {"result": "minimal"}

    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            id="minimal_tool",
            name="Minimal",
            description="Minimal",
            category=ToolCategory.COMPUTATION,
            tool_type=ToolType.EXECUTABLE,
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


def test_register_tool_with_indexing_error():
    """Test tool registration when indexing fails"""

    class BrokenTool(BaseTool):
        def __init__(self, name: str, **kwargs):
            super().__init__(name, **kwargs)
            raise ValueError("Broken initialization")

        async def execute(self, input_data, context=None):
            return {}

        def get_metadata(self):
            return ToolMetadata(
                id="broken",
                name="Broken",
                description="Test",
                category=ToolCategory.COMPUTATION,
                tool_type=ToolType.EXECUTABLE,
            )

    # Should register but fail to index
    ToolRegistry.register("broken_tool", BrokenTool)

    # Tool should be in registry
    assert "broken_tool" in ToolRegistry._tools

    # But not indexed (logged as warning)
    assert "broken_tool" not in ToolRegistry._by_category.get(
        ToolCategory.COMPUTATION, set()
    )


def test_find_tools_with_empty_indexes():
    """Test finding tools when indexes are empty"""
    results = ToolRegistry.find_tools_by_criteria(category=ToolCategory.ANALYSIS)

    assert len(results) == 0


def test_find_tools_with_nonexistent_criteria():
    """Test finding tools with criteria that match nothing"""
    ToolRegistry.register("minimal_tool", MinimalTool)

    # Search for capabilities it doesn't have
    results = ToolRegistry.find_tools_by_criteria(
        capabilities=[ToolCapability.TRANSLATION]
    )

    assert len(results) == 0


def test_find_tools_multiple_capabilities_intersection():
    """Test finding tools with multiple capabilities (all required)"""
    ToolRegistry.register("complex_tool", ComplexTool)

    # Tool has TEXT_ANALYSIS, ENTITY_RECOGNITION, SUMMARIZATION
    results = ToolRegistry.find_tools_by_criteria(
        capabilities=[ToolCapability.TEXT_ANALYSIS, ToolCapability.ENTITY_RECOGNITION]
    )

    assert "complex_tool" in results


def test_find_tools_combined_criteria():
    """Test finding tools with multiple combined criteria"""
    ToolRegistry.register("complex_tool", ComplexTool)
    ToolRegistry.register("minimal_tool", MinimalTool)

    # Find ANALYSIS tools with TEXT_ANALYSIS capability
    results = ToolRegistry.find_tools_by_criteria(
        category=ToolCategory.ANALYSIS,
        capabilities=[ToolCapability.TEXT_ANALYSIS],
        tool_type=ToolType.HYBRID,
    )

    assert "complex_tool" in results
    assert "minimal_tool" not in results


def test_find_tools_by_llm_requirement_true():
    """Test finding tools that require LLM"""
    ToolRegistry.register("complex_tool", ComplexTool)
    ToolRegistry.register("minimal_tool", MinimalTool)

    results = ToolRegistry.find_tools_by_criteria(requires_llm=True)

    assert "complex_tool" in results
    assert "minimal_tool" not in results


def test_find_tools_by_llm_requirement_false():
    """Test finding tools that don't require LLM"""
    ToolRegistry.register("complex_tool", ComplexTool)
    ToolRegistry.register("minimal_tool", MinimalTool)

    results = ToolRegistry.find_tools_by_criteria(requires_llm=False)

    assert "minimal_tool" in results
    assert "complex_tool" not in results


def test_create_singleton_with_different_dependencies():
    """Test singleton behavior with different dependency injection"""
    ToolRegistry.register("minimal_tool", MinimalTool)

    mock_service1 = {"type": "service1"}
    mock_service2 = {"type": "service2"}

    # Create singleton with first service
    tool1 = ToolRegistry.create(
        "minimal_tool", singleton=True, llm_service=mock_service1
    )

    # Create singleton with second service (should return same instance)
    tool2 = ToolRegistry.create(
        "minimal_tool", singleton=True, llm_service=mock_service2
    )

    assert tool1 is tool2
    # First service should be preserved
    assert tool1.llm_service == mock_service1


def test_create_non_singleton_with_dependencies():
    """Test non-singleton creates new instances with different dependencies"""
    ToolRegistry.register("minimal_tool", MinimalTool)

    mock_service1 = {"type": "service1"}
    mock_service2 = {"type": "service2"}

    tool1 = ToolRegistry.create(
        "minimal_tool", singleton=False, llm_service=mock_service1
    )
    tool2 = ToolRegistry.create(
        "minimal_tool", singleton=False, llm_service=mock_service2
    )

    assert tool1 is not tool2
    assert tool1.llm_service == mock_service1
    assert tool2.llm_service == mock_service2


def test_get_all_tools_metadata():
    """Test getting metadata for all registered tools"""
    ToolRegistry.register("complex_tool", ComplexTool)
    ToolRegistry.register("minimal_tool", MinimalTool)

    all_tools = ToolRegistry.get_all_tools()

    assert len(all_tools) == 2
    assert "complex_tool" in all_tools
    assert "minimal_tool" in all_tools


def test_index_multiple_capabilities():
    """Test that tool with multiple capabilities is in all capability indexes"""
    ToolRegistry.register("complex_tool", ComplexTool)

    # Should be in TEXT_ANALYSIS index
    assert "complex_tool" in ToolRegistry._by_capability.get(
        ToolCapability.TEXT_ANALYSIS, set()
    )

    # Should be in ENTITY_RECOGNITION index
    assert "complex_tool" in ToolRegistry._by_capability.get(
        ToolCapability.ENTITY_RECOGNITION, set()
    )

    # Should be in SUMMARIZATION index
    assert "complex_tool" in ToolRegistry._by_capability.get(
        ToolCapability.SUMMARIZATION, set()
    )


def test_index_by_category():
    """Test category indexing"""
    ToolRegistry.register("complex_tool", ComplexTool)

    assert "complex_tool" in ToolRegistry._by_category.get(ToolCategory.ANALYSIS, set())


def test_index_by_type():
    """Test type indexing"""
    ToolRegistry.register("complex_tool", ComplexTool)

    assert "complex_tool" in ToolRegistry._by_type.get(ToolType.HYBRID, set())


def test_clear_instances_preserves_registry():
    """Test that clearing instances doesn't affect tool registry"""
    ToolRegistry.register("minimal_tool", MinimalTool)

    # Create singleton
    tool1 = ToolRegistry.create("minimal_tool", singleton=True)

    # Clear instances
    ToolRegistry.clear_instances()

    # Tool should still be registered
    assert ToolRegistry.is_registered("minimal_tool")

    # Creating new singleton should give different instance
    tool2 = ToolRegistry.create("minimal_tool", singleton=True)

    assert tool1 is not tool2


def test_register_duplicate_tool_id():
    """Test registering tool with duplicate ID overwrites"""
    ToolRegistry.register("test_tool", ComplexTool)
    ToolRegistry.register("test_tool", MinimalTool)  # Overwrite

    # Should have MinimalTool
    assert ToolRegistry._tools["test_tool"] == MinimalTool


def test_find_tools_no_criteria():
    """Test finding tools with no criteria returns all tools"""
    ToolRegistry.register("complex_tool", ComplexTool)

    results = ToolRegistry.find_tools_by_criteria()

    # With no criteria, returns all registered tools
    assert len(results) >= 1
    assert "complex_tool" in results


@pytest.mark.asyncio
async def test_tool_with_all_service_dependencies():
    """Test tool with all possible service dependencies"""

    class FullDependencyTool(BaseTool):
        async def execute(self, input_data, context=None):
            return {
                "has_llm": self.llm_service is not None,
                "has_doc": self.document_service is not None,
                "has_vector": self.vector_search_service is not None,
                "has_mcp": self.mcp_service is not None,
                "has_storage": self.storage is not None,
            }

        def get_metadata(self):
            return ToolMetadata(
                id="full_deps",
                name="Full Dependencies",
                description="Test",
                category=ToolCategory.COMPUTATION,
                tool_type=ToolType.HYBRID,
            )

    ToolRegistry.register("full_deps", FullDependencyTool)

    tool = ToolRegistry.create(
        "full_deps",
        singleton=False,
        llm_service={"llm": True},
        document_service={"doc": True},
        vector_search_service={"vector": True},
        mcp_service={"mcp": True},
        storage={"storage": True},
    )

    result = await tool.execute({})

    assert result["has_llm"] is True
    assert result["has_doc"] is True
    assert result["has_vector"] is True
    assert result["has_mcp"] is True
    assert result["has_storage"] is True
