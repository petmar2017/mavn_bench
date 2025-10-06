"""MCP tool adapter - wraps MCP server tools in the unified tool interface"""

import asyncio
import json
from typing import Any, Dict, List, Optional

from ...core.logger import CentralizedLogger
from ..base_tool import (BaseTool, ToolCapability, ToolCategory,
                         ToolExecutionContext, ToolMetadata, ToolType)


class MCPToolAdapter(BaseTool):
    """Adapter to wrap MCP server tools in the unified tool interface

    This adapter allows MCP tools to be used through the same interface
    as native Python tools, LLM tools, and document tools.

    Example:
        @register_tool("mcp_weather")
        class WeatherTool(MCPToolAdapter):
            def __init__(self, name: str, **kwargs):
                super().__init__(
                    name=name,
                    mcp_server_url="http://localhost:3000",
                    mcp_tool_name="get_weather",
                    **kwargs
                )
    """

    def __init__(
        self,
        name: str,
        mcp_server_url: str,
        mcp_tool_name: str,
        description: str = "",
        category: ToolCategory = ToolCategory.COMMUNICATION,
        capabilities: Optional[List[ToolCapability]] = None,
        input_schema: Optional[Dict[str, Any]] = None,
        output_schema: Optional[Dict[str, Any]] = None,
        timeout: int = 30,
        **kwargs,
    ):
        """Initialize MCP tool adapter

        Args:
            name: Tool name/ID
            mcp_server_url: URL of the MCP server
            mcp_tool_name: Name of the tool on the MCP server
            description: Tool description
            category: Tool category
            capabilities: Tool capabilities
            input_schema: Input validation schema
            output_schema: Output schema
            timeout: Request timeout in seconds
            **kwargs: Additional configuration including DI services
        """
        super().__init__(name, **kwargs)

        self.mcp_server_url = mcp_server_url
        self.mcp_tool_name = mcp_tool_name
        self.description = description
        self.category = category
        self.capabilities = capabilities or []
        self.input_schema = input_schema or {}
        self.output_schema = output_schema or {}
        self.timeout = timeout

        self.logger = CentralizedLogger(f"MCPToolAdapter.{name}")

    async def execute(
        self, input_data: Dict[str, Any], context: Optional[ToolExecutionContext] = None
    ) -> Dict[str, Any]:
        """Execute tool via MCP server

        Args:
            input_data: Tool input parameters
            context: Execution context

        Returns:
            Tool execution result

        Raises:
            RuntimeError: If MCP server call fails
        """
        # Validate input
        self.validate_input(input_data)

        # Prepare MCP request
        request_data = {"tool": self.mcp_tool_name, "parameters": input_data}

        # Add context if available
        if context:
            request_data["context"] = {
                "user_id": context.user_id,
                "session_id": context.session_id,
                "trace_id": context.trace_id,
            }

        try:
            # Call MCP server
            import httpx

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.mcp_server_url}/execute", json=request_data
                )
                response.raise_for_status()

                result = response.json()

                self.logger.info(f"MCP tool {self.mcp_tool_name} executed successfully")

                return result

        except httpx.HTTPError as e:
            self.logger.error(f"MCP tool execution failed: {str(e)}")
            raise RuntimeError(f"MCP server call failed: {str(e)}") from e

        except Exception as e:
            self.logger.error(f"Unexpected error in MCP tool: {str(e)}")
            raise RuntimeError(f"Tool execution error: {str(e)}") from e

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata

        Returns:
            Tool metadata
        """
        return ToolMetadata(
            id=self.name,
            name=self.name,
            description=self.description or f"MCP tool: {self.mcp_tool_name}",
            category=self.category,
            capabilities=self.capabilities,
            tool_type=ToolType.MCP,
            input_schema=self.input_schema,
            output_schema=self.output_schema,
            requires_mcp=True,
            is_async=True,
        )

    async def health_check(self) -> Dict[str, Any]:
        """Check if MCP server is healthy

        Returns:
            Health check result
        """
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.mcp_server_url}/health")
                response.raise_for_status()

                return {
                    "status": "healthy",
                    "server": self.mcp_server_url,
                    "tool": self.mcp_tool_name,
                }

        except Exception as e:
            return {
                "status": "unhealthy",
                "server": self.mcp_server_url,
                "error": str(e),
            }
