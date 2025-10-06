"""Translation tool for translating text to English"""

from typing import Dict, Any

from ..base_tool import BaseLLMTool, ToolMetadata, ToolCapability
from ..tool_registry import LLMToolType
from ..tool_decorators import register_tool


@register_tool(LLMToolType.TRANSLATION)
class TranslationTool(BaseLLMTool):
    """Tool for translating text to English"""

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata"""
        return ToolMetadata(
            name="translation",
            description="Translate text from any language to English",
            version="1.0.0",
            capabilities=[
                ToolCapability.TEXT_GENERATION,
                ToolCapability.TEXT_ANALYSIS
            ],
            input_schema={
                "text": {
                    "type": "str",
                    "required": True,
                    "description": "Text to translate to English"
                },
                "source_language": {
                    "type": "str",
                    "required": False,
                    "description": "Source language ISO 639-1 code (optional, will auto-detect)"
                }
            },
            output_schema={
                "translated_text": {
                    "type": "str",
                    "description": "Text translated to English"
                },
                "source_language": {
                    "type": "str",
                    "description": "Detected or provided source language code"
                }
            },
            max_input_length=500000,  # Can handle long documents via chunking
            supports_streaming=False
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute translation

        Args:
            input_data: Must contain 'text', optionally 'source_language'

        Returns:
            Dictionary with 'translated_text' and 'source_language'
        """
        # Validate input
        self.validate_input(input_data)

        # Extract text
        text = input_data.get("text", "")
        source_language = input_data.get("source_language", "auto")

        # Validate text is not empty
        if not text or len(text.strip()) == 0:
            return {
                "translated_text": "",
                "source_language": "unknown"
            }

        # Handle long documents by chunking
        max_chunk_size = 40000  # Leave room for prompt overhead
        if len(text) > max_chunk_size:
            translated_text = await self._translate_in_chunks(text, source_language, max_chunk_size)
        else:
            # Prepare prompt
            prompt = self._prepare_prompt(text, source_language)

            # Call LLM
            if self.llm_client:
                response = await self.call_llm(
                    prompt=prompt,
                    max_tokens=len(text.split()) * 2,  # Rough estimate for translation
                    temperature=0.3  # Low temperature for accuracy
                )
                translated_text = self._parse_translation(response)
            else:
                # Fallback for testing
                translated_text = text  # Return original if no LLM

        return {
            "translated_text": translated_text,
            "source_language": source_language
        }

    def _prepare_prompt(self, text: str, source_language: str) -> str:
        """Prepare the translation prompt"""
        if source_language != "auto":
            prompt_template = """Translate the following {source_language} text to English.
Preserve formatting, structure, and meaning as much as possible.
Return only the English translation without explanations.

Text to translate:
{text}

English translation:"""
        else:
            prompt_template = """Translate the following text to English.
Preserve formatting, structure, and meaning as much as possible.
Return only the English translation without explanations.

Text to translate:
{text}

English translation:"""

        return self.prepare_prompt(
            prompt_template,
            text=text,
            source_language=source_language
        )

    def _parse_translation(self, response: str) -> str:
        """Parse translation result from LLM response"""
        # Remove any leading/trailing whitespace
        translation = response.strip()

        # Remove common prefixes if they exist
        prefixes_to_remove = [
            "english translation:",
            "translation:",
            "here is the translation:",
            "here's the translation:"
        ]

        translation_lower = translation.lower()
        for prefix in prefixes_to_remove:
            if translation_lower.startswith(prefix):
                translation = translation[len(prefix):].strip()
                break

        return translation

    async def _translate_in_chunks(
        self,
        text: str,
        source_language: str,
        chunk_size: int
    ) -> str:
        """Translate long text by processing in chunks

        Args:
            text: Full text to translate
            source_language: Source language code or "auto"
            chunk_size: Maximum size of each chunk

        Returns:
            Complete translated text
        """
        translated_chunks = []

        # Split text into overlapping chunks to maintain context
        overlap = 500  # Characters of overlap between chunks
        chunks = []
        start = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end])
            start = end - overlap if end < len(text) else end

        # Process each chunk
        for chunk in chunks:
            prompt = self._prepare_prompt(chunk, source_language)

            if self.llm_client:
                response = await self.call_llm(
                    prompt=prompt,
                    max_tokens=len(chunk.split()) * 2,  # Rough estimate for translation
                    temperature=0.3  # Low temperature for accuracy
                )
                translated_chunk = self._parse_translation(response)
            else:
                # Fallback for testing
                translated_chunk = chunk

            translated_chunks.append(translated_chunk)

        # Concatenate all translated chunks
        return " ".join(translated_chunks)
