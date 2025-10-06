"""Example LLM tool with dependency injection"""

from typing import Any, Dict, Optional

from ..base_tool import (BaseTool, ToolCapability, ToolCategory,
                         ToolExecutionContext, ToolMetadata, ToolType)
from ..tool_decorators import register_tool


@register_tool("smart_summarize")
class SmartSummarizeTool(BaseTool):
    """Smart summarization tool using LLM service

    This demonstrates dependency injection - the tool requires an llm_service
    to be injected during creation.
    """

    def __init__(self, name: str, llm_service=None, **kwargs):
        """Initialize with required LLM service

        Args:
            name: Tool name
            llm_service: Required LLM service for AI operations
            **kwargs: Additional configuration

        Raises:
            ValueError: If llm_service is not provided
        """
        super().__init__(name, llm_service=llm_service, **kwargs)

        if not self.llm_service:
            raise ValueError("SmartSummarizeTool requires llm_service to be injected")

    async def execute(
        self, input_data: Dict[str, Any], context: Optional[ToolExecutionContext] = None
    ) -> Dict[str, Any]:
        """Generate smart summary using LLM

        Args:
            input_data: Must contain 'text' and optional 'max_length'
            context: Execution context

        Returns:
            Dict with summary and metadata
        """
        self.validate_input(input_data)

        text = input_data.get("text", "")
        max_length = input_data.get("max_length", 200)

        # Use injected LLM service
        summary = await self.llm_service.summarize(
            text=text,
            max_length=max_length,
            trace_id=context.trace_id if context else None,
        )

        return {
            "summary": summary,
            "original_length": len(text),
            "summary_length": len(summary),
            "compression_ratio": len(summary) / len(text) if text else 0,
        }

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata"""
        return ToolMetadata(
            id="smart_summarize",
            name="Smart Summarization",
            description="Generate intelligent summaries using LLM",
            version="1.0.0",
            category=ToolCategory.LLM,
            capabilities=[ToolCapability.TEXT_GENERATION, ToolCapability.SUMMARIZATION],
            tool_type=ToolType.LLM,
            input_schema={
                "text": {
                    "type": "str",
                    "required": True,
                    "description": "Text to summarize",
                },
                "max_length": {
                    "type": "int",
                    "required": False,
                    "description": "Maximum summary length",
                    "default": 200,
                },
            },
            output_schema={
                "summary": {"type": "str", "description": "Generated summary"},
                "original_length": {
                    "type": "int",
                    "description": "Length of original text",
                },
                "summary_length": {"type": "int", "description": "Length of summary"},
                "compression_ratio": {
                    "type": "float",
                    "description": "Ratio of summary to original length",
                },
            },
            requires_llm=True,
            execution_time_estimate="medium",
            is_async=True,
            examples=[
                {
                    "input": {"text": "Long document text...", "max_length": 100},
                    "output": {
                        "summary": "Brief summary...",
                        "original_length": 1000,
                        "summary_length": 95,
                        "compression_ratio": 0.095,
                    },
                }
            ],
        )
