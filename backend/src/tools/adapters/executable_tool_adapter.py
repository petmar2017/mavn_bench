"""Executable tool adapter - wraps Python scripts and binaries in the unified tool interface"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...core.logger import CentralizedLogger
from ..base_tool import (BaseTool, ToolCapability, ToolCategory,
                         ToolExecutionContext, ToolMetadata, ToolType)


class ExecutableToolAdapter(BaseTool):
    """Adapter to wrap executable programs (Python scripts, binaries) in the unified tool interface

    This adapter allows executable programs to be used through the same interface
    as LLM tools, MCP tools, and document tools.

    The executable should:
    - Accept JSON input via stdin or as a file
    - Output JSON result via stdout
    - Exit with code 0 for success, non-zero for failure

    Example:
        @register_tool("word_count")
        class WordCountTool(ExecutableToolAdapter):
            def __init__(self, name: str, **kwargs):
                super().__init__(
                    name=name,
                    executable_path="./tools/word_count.py",
                    executable_type="python",
                    **kwargs
                )
    """

    def __init__(
        self,
        name: str,
        executable_path: str,
        executable_type: str = "python",
        description: str = "",
        category: ToolCategory = ToolCategory.COMPUTATION,
        capabilities: Optional[List[ToolCapability]] = None,
        input_schema: Optional[Dict[str, Any]] = None,
        output_schema: Optional[Dict[str, Any]] = None,
        input_mode: str = "stdin",
        output_mode: str = "stdout",
        timeout: int = 30,
        **kwargs,
    ):
        """Initialize executable tool adapter

        Args:
            name: Tool name/ID
            executable_path: Path to executable (script or binary)
            executable_type: Type of executable ("python", "node", "binary", etc.)
            description: Tool description
            category: Tool category
            capabilities: Tool capabilities
            input_schema: Input validation schema
            output_schema: Output schema
            input_mode: How to pass input ("stdin" or "file")
            output_mode: How to read output ("stdout" or "file")
            timeout: Execution timeout in seconds
            **kwargs: Additional configuration including DI services
        """
        super().__init__(name, **kwargs)

        self.executable_path = Path(executable_path)
        self.executable_type = executable_type
        self.description = description
        self.category = category
        self.capabilities = capabilities or []
        self.input_schema = input_schema or {}
        self.output_schema = output_schema or {}
        self.input_mode = input_mode
        self.output_mode = output_mode
        self.timeout = timeout

        self.logger = CentralizedLogger(f"ExecutableToolAdapter.{name}")

        # Validate executable exists
        if not self.executable_path.exists():
            raise ValueError(f"Executable not found: {self.executable_path}")

    def _build_command(self) -> List[str]:
        """Build command to execute

        Returns:
            Command as list of strings
        """
        if self.executable_type == "python":
            return [sys.executable, str(self.executable_path)]
        elif self.executable_type == "node":
            return ["node", str(self.executable_path)]
        elif self.executable_type == "binary":
            return [str(self.executable_path)]
        else:
            raise ValueError(f"Unsupported executable type: {self.executable_type}")

    async def execute(
        self, input_data: Dict[str, Any], context: Optional[ToolExecutionContext] = None
    ) -> Dict[str, Any]:
        """Execute tool via subprocess

        Args:
            input_data: Tool input parameters
            context: Execution context

        Returns:
            Tool execution result

        Raises:
            RuntimeError: If execution fails
        """
        # Validate input
        self.validate_input(input_data)

        # Prepare input data
        execution_data = {"input": input_data}
        if context:
            execution_data["context"] = {
                "user_id": context.user_id,
                "session_id": context.session_id,
                "trace_id": context.trace_id,
            }

        input_json = json.dumps(execution_data)

        try:
            # Build command
            cmd = self._build_command()

            # Execute subprocess
            if self.input_mode == "stdin":
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input_json.encode()), timeout=self.timeout
                )

            else:  # file mode
                # Write input to temp file
                import tempfile

                with tempfile.NamedTemporaryFile(
                    mode="w", delete=False, suffix=".json"
                ) as f:
                    f.write(input_json)
                    input_file = f.name

                try:
                    cmd.append(input_file)

                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )

                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(), timeout=self.timeout
                    )

                finally:
                    # Clean up temp file
                    Path(input_file).unlink(missing_ok=True)

            # Check return code
            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                self.logger.error(
                    f"Executable failed with code {process.returncode}: {error_msg}"
                )
                raise RuntimeError(f"Execution failed: {error_msg}")

            # Parse output
            if self.output_mode == "stdout":
                output = stdout.decode()
                result = json.loads(output)
            else:  # file mode
                # Executable should write to a known location
                output_file = self.executable_path.parent / f"{self.name}_output.json"
                with output_file.open() as f:
                    result = json.load(f)
                output_file.unlink(missing_ok=True)

            self.logger.info(f"Executable tool {self.name} executed successfully")

            return result

        except asyncio.TimeoutError:
            self.logger.error(f"Executable timed out after {self.timeout}s")
            raise RuntimeError(f"Execution timeout after {self.timeout}s")

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse output JSON: {str(e)}")
            raise RuntimeError(f"Invalid JSON output: {str(e)}") from e

        except Exception as e:
            self.logger.error(f"Unexpected error in executable tool: {str(e)}")
            raise RuntimeError(f"Tool execution error: {str(e)}") from e

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata

        Returns:
            Tool metadata
        """
        return ToolMetadata(
            id=self.name,
            name=self.name,
            description=self.description
            or f"Executable tool: {self.executable_path.name}",
            category=self.category,
            capabilities=self.capabilities,
            tool_type=ToolType.EXECUTABLE,
            input_schema=self.input_schema,
            output_schema=self.output_schema,
            is_async=True,
        )

    async def health_check(self) -> Dict[str, Any]:
        """Check if executable is accessible

        Returns:
            Health check result
        """
        if not self.executable_path.exists():
            return {
                "status": "unhealthy",
                "executable": str(self.executable_path),
                "error": "Executable not found",
            }

        if not self.executable_path.is_file():
            return {
                "status": "unhealthy",
                "executable": str(self.executable_path),
                "error": "Path is not a file",
            }

        return {
            "status": "healthy",
            "executable": str(self.executable_path),
            "type": self.executable_type,
        }
