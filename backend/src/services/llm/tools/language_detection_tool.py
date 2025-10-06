"""Language detection tool for identifying text language"""

from typing import Dict, Any, Tuple

from ..base_tool import BaseLLMTool, ToolMetadata, ToolCapability
from ..tool_registry import LLMToolType
from ..tool_decorators import register_tool


@register_tool(LLMToolType.LANGUAGE_DETECTION)
class LanguageDetectionTool(BaseLLMTool):
    """Tool for detecting the language of text"""

    def get_metadata(self) -> ToolMetadata:
        """Get tool metadata"""
        return ToolMetadata(
            name="language_detection",
            description="Detect the language of text and return ISO 639-1 code",
            version="1.0.0",
            capabilities=[
                ToolCapability.CLASSIFICATION,
                ToolCapability.TEXT_ANALYSIS
            ],
            input_schema={
                "text": {
                    "type": "str",
                    "required": True,
                    "description": "Text to analyze for language detection"
                }
            },
            output_schema={
                "language": {
                    "type": "str",
                    "description": "ISO 639-1 language code (e.g., 'en', 'es', 'fr')"
                },
                "confidence": {
                    "type": "float",
                    "description": "Confidence score (0-1)"
                }
            },
            max_input_length=1000000,  # Can handle any size (only uses first 500 chars)
            supports_streaming=False
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute language detection

        Args:
            input_data: Must contain 'text'

        Returns:
            Dictionary with 'language' and 'confidence' keys
        """
        # Validate input
        self.validate_input(input_data)

        # Extract text
        text = input_data.get("text", "")

        # Validate text is not empty
        if not text or len(text.strip()) == 0:
            return {"language": "unknown", "confidence": 0.0}

        # Prepare prompt
        prompt = self._prepare_prompt(text)

        # Call LLM
        if self.llm_client:
            response = await self.call_llm(
                prompt=prompt,
                max_tokens=50,  # Language detection needs minimal tokens
                temperature=0.1  # Very low temperature for consistency
            )
            language, confidence = self._parse_language(response)
        else:
            # Fallback for testing
            language, confidence = self._detect_language_fallback(text)

        return {
            "language": language,
            "confidence": confidence
        }

    def _prepare_prompt(self, text: str) -> str:
        """Prepare the language detection prompt"""
        prompt_template = """Detect the language of the following text.

Return only the ISO 639-1 language code and confidence score.
Common codes: 'en' (English), 'es' (Spanish), 'fr' (French), 'de' (German),
'zh' (Chinese), 'ja' (Japanese), 'ko' (Korean), 'ar' (Arabic), 'ru' (Russian),
'pt' (Portuguese), 'it' (Italian), 'nl' (Dutch), 'sv' (Swedish), 'pl' (Polish).

Format your response exactly as:
Language: [code]
Confidence: [score]

Text to analyze:
{text}

Response:"""

        return self.prepare_prompt(
            prompt_template,
            text=text[:500]  # Only need a sample for language detection
        )

    def _parse_language(self, response: str) -> Tuple[str, float]:
        """Parse language detection result from LLM response"""
        language = "en"  # Default to English
        confidence = 0.5

        lines = response.strip().split('\n')
        for line in lines:
            line_lower = line.lower()

            # Parse language code
            if "language:" in line_lower:
                lang_text = line.split(':', 1)[1].strip().lower()
                # Extract just the language code (first 2-3 characters)
                # Remove any additional text
                lang_code = lang_text.split()[0] if lang_text else "en"
                # Ensure it's a valid ISO 639-1 code format
                if len(lang_code) >= 2:
                    language = lang_code[:2]

            # Parse confidence
            elif "confidence:" in line_lower:
                try:
                    conf_text = line.split(':', 1)[1].strip()
                    # Handle percentage format
                    if '%' in conf_text:
                        confidence = float(conf_text.replace('%', '').strip()) / 100
                    else:
                        confidence = float(conf_text)
                    # Ensure confidence is in valid range
                    confidence = min(1.0, max(0.0, confidence))
                except (ValueError, IndexError):
                    confidence = 0.8

        return (language, confidence)

    def _detect_language_fallback(self, text: str) -> Tuple[str, float]:
        """Simple language detection based on character patterns and common words"""
        text_lower = text.lower()

        # Common words in different languages
        language_patterns = {
            "en": ["the", "and", "is", "in", "to", "of", "a", "that", "it", "for"],
            "es": ["el", "la", "de", "que", "y", "en", "un", "por", "con", "para"],
            "fr": ["le", "de", "un", "et", "être", "avoir", "que", "pour", "dans", "ce"],
            "de": ["der", "die", "das", "und", "in", "den", "von", "zu", "mit", "sich"],
            "it": ["il", "di", "e", "che", "la", "in", "un", "per", "con", "non"],
            "pt": ["o", "de", "e", "que", "do", "da", "em", "um", "para", "com"],
            "nl": ["de", "het", "een", "van", "en", "in", "is", "op", "aan", "met"],
            "ru": ["и", "в", "не", "на", "я", "с", "что", "это", "по", "к"],
            "ja": ["の", "は", "を", "が", "に", "で", "と", "から", "も", "や"],
            "zh": ["的", "是", "在", "和", "了", "有", "我", "不", "这", "个"],
            "ar": ["في", "من", "على", "إلى", "أن", "هذا", "التي", "ما", "عن", "مع"],
            "ko": ["이", "그", "은", "는", "을", "를", "의", "에", "와", "과"]
        }

        # Count matches for each language
        scores = {}
        for lang, words in language_patterns.items():
            score = 0
            for word in words:
                if lang in ["ja", "zh", "ar", "ko", "ru"]:
                    # For non-Latin scripts, check character presence
                    if word in text:
                        score += 1
                else:
                    # For Latin scripts, check word boundaries
                    if f" {word} " in f" {text_lower} ":
                        score += 1

            scores[lang] = score / len(words) if words else 0

        # Find language with highest score
        if scores:
            best_lang = max(scores, key=scores.get)
            best_score = scores[best_lang]

            if best_score > 0:
                # Convert score to confidence
                confidence = min(0.95, 0.5 + best_score * 0.45)
                return (best_lang, confidence)

        # Default to English with low confidence
        return ("en", 0.3)