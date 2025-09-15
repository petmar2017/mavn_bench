"""Summarization tool for generating text summaries"""

from typing import Dict, Any, List

from ..base_tool import BaseLLMTool, ToolMetadata, ToolCapability
from ..tool_registry import LLMToolType
from ..tool_decorators import register_tool


@register_tool(LLMToolType.SUMMARIZATION)
class SummarizationTool(BaseLLMTool):
    """Tool for generating text summaries"""

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata"""
        return ToolMetadata(
            name="summarization",
            description="Generate concise or detailed summaries of text",
            version="1.0.0",
            capabilities=[
                ToolCapability.TEXT_GENERATION,
                ToolCapability.TEXT_ANALYSIS
            ],
            input_schema={
                "text": {
                    "type": "str",
                    "required": True,
                    "description": "Text to summarize"
                },
                "max_length": {
                    "type": "int",
                    "required": False,
                    "default": 500,
                    "description": "Maximum length of summary in words"
                },
                "style": {
                    "type": "str",
                    "required": False,
                    "default": "concise",
                    "description": "Summary style: concise, detailed, or bullet_points"
                }
            },
            output_schema={
                "summary": {
                    "type": "str",
                    "description": "Generated summary"
                }
            },
            max_input_length=50000,
            supports_streaming=False
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute summarization

        Args:
            input_data: Must contain 'text', optionally 'max_length' and 'style'

        Returns:
            Dictionary with 'summary' key
        """
        # Validate input
        self.validate_input(input_data)

        # Extract parameters
        text = input_data.get("text", "")
        max_length = input_data.get("max_length", 500)
        style = input_data.get("style", "concise")

        # Validate text is not empty
        if not text or len(text.strip()) == 0:
            return {"summary": "No text provided for summarization."}

        # Prepare prompt
        prompt = self._prepare_prompt(text, max_length, style)

        # Call LLM
        if self.llm_client:
            summary = await self.call_llm(
                prompt=prompt,
                max_tokens=max_length * 2,  # Approximate tokens
                temperature=0.5
            )
        else:
            # Fallback for testing
            summary = self._generate_fallback_summary(text, max_length)

        return {"summary": summary}

    def _prepare_prompt(self, text: str, max_length: int, style: str) -> str:
        """Prepare the summarization prompt"""
        style_instructions = {
            "concise": "Provide a concise summary highlighting key points.",
            "detailed": "Provide a detailed summary covering all major topics.",
            "bullet_points": "Provide a summary in bullet point format."
        }

        instruction = style_instructions.get(style, style_instructions["concise"])

        prompt_template = """Please summarize the following text. {instruction}
Maximum length: approximately {max_length} words.

Text:
{text}

Summary:"""

        return self.prepare_prompt(
            prompt_template,
            instruction=instruction,
            max_length=max_length,
            text=text[:10000]  # Limit text length for prompt
        )

    def _generate_fallback_summary(self, text: str, max_length: int) -> str:
        """Generate a basic summary without LLM"""
        # Simple fallback: take first few sentences
        sentences = text.split('. ')
        word_count = 0
        summary_sentences = []

        for sentence in sentences:
            words_in_sentence = len(sentence.split())
            if word_count + words_in_sentence <= max_length:
                summary_sentences.append(sentence)
                word_count += words_in_sentence
            else:
                break

        if summary_sentences:
            summary = '. '.join(summary_sentences)
            if not summary.endswith('.'):
                summary += '.'
            return summary
        else:
            # If no complete sentences fit, truncate
            words = text.split()[:max_length]
            return ' '.join(words) + '...'