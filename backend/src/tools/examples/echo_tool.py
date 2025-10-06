"""Example executable tool - echo command"""

from typing import Any, Dict, Optional

from ..base_tool import (BaseTool, ToolCapability, ToolCategory,
                         ToolExecutionContext, ToolMetadata, ToolType)
from ..tool_decorators import register_tool


@register_tool("echo")
class EchoTool(BaseTool):
    """Simple example tool that echoes input back

    This demonstrates a basic tool without external dependencies.
    """

    async def execute(
        self, input_data: Dict[str, Any], context: Optional[ToolExecutionContext] = None
    ) -> Dict[str, Any]:
        """Echo input data back

        Args:
            input_data: Must contain 'message' field
            context: Execution context

        Returns:
            Dict with echoed message and metadata
        """
        self.validate_input(input_data)

        message = input_data.get("message", "")

        return {
            "echoed_message": message,
            "message_length": len(message),
            "context_id": context.trace_id if context else None,
        }

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata"""
        return ToolMetadata(
            id="echo",
            name="Echo Tool",
            description="Echoes input message back with metadata",
            version="1.0.0",
            category=ToolCategory.COMPUTATION,
            capabilities=[ToolCapability.TEXT_ANALYSIS],
            tool_type=ToolType.EXECUTABLE,
            input_schema={
                "message": {
                    "type": "str",
                    "required": True,
                    "description": "Message to echo",
                }
            },
            output_schema={
                "echoed_message": {"type": "str", "description": "The echoed message"},
                "message_length": {
                    "type": "int",
                    "description": "Length of the message",
                },
                "context_id": {"type": "str", "description": "Trace ID from context"},
            },
            execution_time_estimate="fast",
            is_async=True,
            examples=[
                {
                    "input": {"message": "Hello, World!"},
                    "output": {
                        "echoed_message": "Hello, World!",
                        "message_length": 13,
                        "context_id": None,
                    },
                }
            ],
        )
