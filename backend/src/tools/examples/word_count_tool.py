"""Example executable tool - word count"""

from typing import Any, Dict, Optional

from ..base_tool import (BaseTool, ToolCapability, ToolCategory,
                         ToolExecutionContext, ToolMetadata, ToolType)
from ..tool_decorators import register_tool


@register_tool("word_count")
class WordCountTool(BaseTool):
    """Simple example tool that counts words in text

    This is a native Python implementation (not an executable adapter)
    demonstrating how to create custom tools.
    """

    async def execute(
        self, input_data: Dict[str, Any], context: Optional[ToolExecutionContext] = None
    ) -> Dict[str, Any]:
        """Count words in text

        Args:
            input_data: Must contain 'text' field
            context: Execution context

        Returns:
            Dict with word_count, character_count, line_count
        """
        self.validate_input(input_data)

        text = input_data.get("text", "")

        # Count metrics
        words = text.split()
        lines = text.split("\n")

        return {
            "word_count": len(words),
            "character_count": len(text),
            "line_count": len(lines),
            "unique_words": len(set(word.lower() for word in words)),
        }

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata"""
        return ToolMetadata(
            id="word_count",
            name="Word Counter",
            description="Count words, characters, and lines in text",
            version="1.0.0",
            category=ToolCategory.ANALYSIS,
            capabilities=[ToolCapability.TEXT_ANALYSIS],
            tool_type=ToolType.EXECUTABLE,
            input_schema={
                "text": {
                    "type": "str",
                    "required": True,
                    "description": "Text to analyze",
                }
            },
            output_schema={
                "word_count": {"type": "int", "description": "Number of words"},
                "character_count": {
                    "type": "int",
                    "description": "Number of characters",
                },
                "line_count": {"type": "int", "description": "Number of lines"},
                "unique_words": {
                    "type": "int",
                    "description": "Number of unique words (case-insensitive)",
                },
            },
            execution_time_estimate="fast",
            is_async=True,
            examples=[
                {
                    "input": {"text": "Hello world! Hello universe!"},
                    "output": {
                        "word_count": 4,
                        "character_count": 28,
                        "line_count": 1,
                        "unique_words": 3,
                    },
                }
            ],
        )
