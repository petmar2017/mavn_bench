"""Markdown formatting tool for converting text to well-formatted markdown"""

from typing import Dict, Any, List

from ..base_tool import BaseLLMTool, ToolMetadata, ToolCapability
from ..tool_registry import LLMToolType
from ..tool_decorators import register_tool


@register_tool(
    LLMToolType.MARKDOWN_FORMATTING,
    aliases=[LLMToolType.TEXT_TO_MARKDOWN]
)
class MarkdownFormattingTool(BaseLLMTool):
    """Tool for converting plain text to well-formatted markdown"""

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata"""
        return ToolMetadata(
            name="markdown_formatting",
            description="Convert plain text to well-formatted markdown",
            version="1.0.0",
            capabilities=[
                ToolCapability.TEXT_TRANSFORMATION,
                ToolCapability.TEXT_GENERATION
            ],
            input_schema={
                "text": {
                    "type": "str",
                    "required": True,
                    "description": "Plain text to convert to markdown"
                },
                "preserve_structure": {
                    "type": "bool",
                    "required": False,
                    "default": True,
                    "description": "Whether to preserve original text structure"
                }
            },
            output_schema={
                "markdown": {
                    "type": "str",
                    "description": "Formatted markdown text"
                }
            },
            max_input_length=50000,
            supports_streaming=False
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute markdown formatting

        Args:
            input_data: Must contain 'text', optionally 'preserve_structure'

        Returns:
            Dictionary with 'markdown' key
        """
        # Validate input
        self.validate_input(input_data)

        # Extract parameters
        text = input_data.get("text", "")
        preserve_structure = input_data.get("preserve_structure", True)

        # Validate text is not empty
        if not text or len(text.strip()) == 0:
            return {"markdown": ""}

        # Prepare prompt
        prompt = self._prepare_prompt(text, preserve_structure)

        # Call LLM
        if self.llm_client:
            markdown = await self.call_llm(
                prompt=prompt,
                max_tokens=len(text) * 2,  # Allow for expansion
                temperature=0.3  # Lower temperature for consistent formatting
            )
        else:
            # Fallback for testing
            markdown = self._generate_fallback_markdown(text)

        return {"markdown": markdown}

    def _prepare_prompt(self, text: str, preserve_structure: bool) -> str:
        """Prepare the markdown formatting prompt"""
        structure_instruction = (
            "Preserve the original structure and content of the text."
            if preserve_structure
            else "Feel free to reorganize for better readability."
        )

        prompt_template = """Convert this plain text to well-formatted markdown.

Rules:
1. Add appropriate headers (##) for sections
2. Use bullet points or numbered lists where appropriate
3. Add emphasis (bold/italic) for important terms
4. Preserve code blocks if any (use ```)
5. Keep the original content intact, just improve formatting
6. Make it easy to read and navigate
7. {structure_instruction}

Text:
{text}

Return only the formatted markdown, no explanations."""

        return self.prepare_prompt(
            prompt_template,
            structure_instruction=structure_instruction,
            text=text[:8000]  # Limit text length for prompt
        )

    def _generate_fallback_markdown(self, text: str) -> str:
        """Generate basic markdown formatting without LLM"""
        lines = text.split('\n')
        formatted = []

        in_code_block = False
        consecutive_empty = 0

        for line in lines:
            stripped = line.strip()

            # Handle empty lines
            if not stripped:
                consecutive_empty += 1
                if consecutive_empty <= 1:  # Keep max 1 empty line
                    formatted.append('')
                continue
            else:
                consecutive_empty = 0

            # Detect code blocks
            if line.startswith('    ') or line.startswith('\t'):
                if not in_code_block:
                    formatted.append('```')
                    in_code_block = True
                formatted.append(line)
                continue
            elif in_code_block:
                formatted.append('```')
                in_code_block = False

            # Headers: uppercase lines less than 100 chars
            if stripped.isupper() and len(stripped) < 100:
                formatted.append(f"## {stripped.title()}")
            # Lists: lines starting with common list markers
            elif stripped.startswith(('- ', '* ', '• ')):
                formatted.append(stripped)
            # Numbered lists
            elif any(stripped.startswith(f"{i}.") for i in range(1, 10)):
                formatted.append(stripped)
            # Regular paragraphs
            else:
                # Add some basic formatting
                # Bold important terms (simple heuristic: capitalized words)
                words = stripped.split()
                formatted_words = []
                for word in words:
                    if word.isupper() and len(word) > 2:
                        formatted_words.append(f"**{word}**")
                    else:
                        formatted_words.append(word)
                formatted.append(' '.join(formatted_words))

        # Close any open code blocks
        if in_code_block:
            formatted.append('```')

        return '\n'.join(formatted)