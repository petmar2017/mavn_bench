"""Tests for LLM tools with focus on edge cases and chunking functionality"""

import pytest
from unittest.mock import AsyncMock, Mock

from src.services.llm.tools.entity_extraction_tool import EntityExtractionTool, Entity
from src.services.llm.tools.language_detection_tool import LanguageDetectionTool
from src.services.llm.tools.translation_tool import TranslationTool


class TestEntityExtractionTool:
    """Test entity extraction tool including chunking functionality"""

    @pytest.fixture
    def entity_tool(self):
        """Create entity extraction tool instance"""
        tool = EntityExtractionTool(name="entity_extraction")
        # Mock LLM client for testing
        tool.llm_client = AsyncMock()
        return tool

    @pytest.mark.asyncio
    async def test_service_initialization(self, entity_tool):
        """Test tool initializes correctly"""
        assert entity_tool is not None
        metadata = entity_tool.get_metadata()
        assert metadata.name == "entity_extraction"
        assert metadata.max_input_length == 500000
        assert metadata.supports_streaming is False

    @pytest.mark.asyncio
    async def test_empty_text_handling(self, entity_tool):
        """Test handling of empty text input"""
        result = await entity_tool.execute({"text": ""})
        assert result == {"entities": []}

        result = await entity_tool.execute({"text": "   "})
        assert result == {"entities": []}

    @pytest.mark.asyncio
    async def test_short_text_extraction(self, entity_tool):
        """Test entity extraction for short text (no chunking)"""
        text = "John Smith works at Google in San Francisco."

        # Mock LLM response
        entity_tool.llm_client.chat.completions.create = AsyncMock(
            return_value=Mock(
                choices=[Mock(message=Mock(content='[{"text": "John Smith", "type": "PERSON", "confidence": 0.95}, {"text": "Google", "type": "ORGANIZATION", "confidence": 0.98}, {"text": "San Francisco", "type": "LOCATION", "confidence": 0.92}]'))]
            )
        )

        result = await entity_tool.execute({"text": text})

        assert "entities" in result
        assert len(result["entities"]) == 3
        assert any(e["text"] == "John Smith" and e["type"] == "PERSON" for e in result["entities"])
        assert any(e["text"] == "Google" and e["type"] == "ORGANIZATION" for e in result["entities"])

    @pytest.mark.asyncio
    async def test_long_text_chunking(self, entity_tool):
        """Test entity extraction with long text requiring chunking"""
        # Create text longer than 40,000 characters
        base_text = "John Smith works at Google. " * 100
        long_text = base_text * 15  # ~42,000 characters

        # Mock LLM response for each chunk
        entity_tool.llm_client.chat.completions.create = AsyncMock(
            return_value=Mock(
                choices=[Mock(message=Mock(content='[{"text": "John Smith", "type": "PERSON", "confidence": 0.95}, {"text": "Google", "type": "ORGANIZATION", "confidence": 0.98}]'))]
            )
        )

        result = await entity_tool.execute({"text": long_text})

        assert "entities" in result
        assert len(result["entities"]) >= 2
        # Verify deduplication worked (should not have multiple John Smith entries)
        person_entities = [e for e in result["entities"] if e["type"] == "PERSON"]
        assert len(person_entities) <= 1

    @pytest.mark.asyncio
    async def test_entity_deduplication(self, entity_tool):
        """Test that duplicate entities are deduplicated with highest confidence"""
        text = "Test text"

        # Create mock that returns same entity with different confidence scores
        call_count = [0]

        async def mock_llm(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return Mock(choices=[Mock(message=Mock(content='[{"text": "John Smith", "type": "PERSON", "confidence": 0.85}]'))])
            else:
                return Mock(choices=[Mock(message=Mock(content='[{"text": "John Smith", "type": "PERSON", "confidence": 0.95}]'))])

        entity_tool.llm_client.chat.completions.create = mock_llm

        # Use long text to trigger chunking
        long_text = "John Smith " * 15000
        result = await entity_tool.execute({"text": long_text})

        # Should only have one John Smith with highest confidence
        person_entities = [e for e in result["entities"] if e["text"] == "John Smith"]
        assert len(person_entities) == 1
        assert person_entities[0]["confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_fallback_without_llm(self, entity_tool):
        """Test fallback entity extraction without LLM client"""
        entity_tool.llm_client = None

        text = "Contact us at john@example.com or call 555-123-4567. Payment of $100.50 due by Jan 15, 2024."

        result = await entity_tool.execute({"text": text})

        assert "entities" in result
        # Should extract email, phone, money, date using patterns
        entities = result["entities"]
        assert any(e["type"] == "EMAIL" for e in entities)
        assert any(e["type"] == "PHONE" for e in entities)
        assert any(e["type"] == "MONEY" for e in entities)

    @pytest.mark.asyncio
    async def test_custom_entity_types(self, entity_tool):
        """Test extraction with custom entity types"""
        text = "Test text"
        entity_types = ["PERSON", "LOCATION"]

        entity_tool.llm_client.chat.completions.create = AsyncMock(
            return_value=Mock(
                choices=[Mock(message=Mock(content='[{"text": "Test Entity", "type": "PERSON", "confidence": 0.9}]'))]
            )
        )

        result = await entity_tool.execute({
            "text": text,
            "entity_types": entity_types
        })

        assert "entities" in result


class TestLanguageDetectionTool:
    """Test language detection tool including edge cases"""

    @pytest.fixture
    def language_tool(self):
        """Create language detection tool instance"""
        tool = LanguageDetectionTool(name="language_detection")
        tool.llm_client = AsyncMock()
        return tool

    @pytest.mark.asyncio
    async def test_service_initialization(self, language_tool):
        """Test tool initializes correctly"""
        assert language_tool is not None
        metadata = language_tool.get_metadata()
        assert metadata.name == "language_detection"
        assert metadata.max_input_length == 1000000
        assert metadata.supports_streaming is False

    @pytest.mark.asyncio
    async def test_empty_text_handling(self, language_tool):
        """Test handling of empty text input"""
        result = await language_tool.execute({"text": ""})
        assert result == {"language": "unknown", "confidence": 0.0}

    @pytest.mark.asyncio
    async def test_english_detection(self, language_tool):
        """Test English language detection"""
        text = "This is a test in English."

        language_tool.llm_client.chat.completions.create = AsyncMock(
            return_value=Mock(
                choices=[Mock(message=Mock(content='Language: en\nConfidence: 0.95'))]
            )
        )

        result = await language_tool.execute({"text": text})

        assert result["language"] == "en"
        assert result["confidence"] >= 0.9

    @pytest.mark.asyncio
    async def test_very_long_text(self, language_tool):
        """Test language detection with very long text (only uses first 500 chars)"""
        # Create text longer than 1 million characters
        long_text = "This is English text. " * 50000  # ~1.1 million characters

        language_tool.llm_client.chat.completions.create = AsyncMock(
            return_value=Mock(
                choices=[Mock(message=Mock(content='Language: en\nConfidence: 0.95'))]
            )
        )

        # Should not raise error even with very long text
        result = await language_tool.execute({"text": long_text})

        assert result["language"] == "en"
        assert result["confidence"] > 0

    @pytest.mark.asyncio
    async def test_fallback_detection_english(self, language_tool):
        """Test fallback language detection for English without LLM"""
        language_tool.llm_client = None

        text = "The quick brown fox jumps over the lazy dog. This is a test of the emergency broadcast system."

        result = await language_tool.execute({"text": text})

        assert result["language"] == "en"
        assert result["confidence"] > 0.5

    @pytest.mark.asyncio
    async def test_fallback_detection_spanish(self, language_tool):
        """Test fallback language detection for Spanish without LLM"""
        language_tool.llm_client = None

        text = "El rápido zorro marrón salta sobre el perro perezoso. La casa es muy grande y bonita."

        result = await language_tool.execute({"text": text})

        assert result["language"] == "es"
        assert result["confidence"] > 0.3

    @pytest.mark.asyncio
    async def test_confidence_score_parsing(self, language_tool):
        """Test parsing different confidence score formats"""
        text = "Test text"

        # Test percentage format
        language_tool.llm_client.chat.completions.create = AsyncMock(
            return_value=Mock(
                choices=[Mock(message=Mock(content='Language: en\nConfidence: 95%'))]
            )
        )

        result = await language_tool.execute({"text": text})
        assert result["confidence"] == 0.95


class TestTranslationTool:
    """Test translation tool including chunking functionality"""

    @pytest.fixture
    def translation_tool(self):
        """Create translation tool instance"""
        tool = TranslationTool(name="translation")
        tool.llm_client = AsyncMock()
        return tool

    @pytest.mark.asyncio
    async def test_service_initialization(self, translation_tool):
        """Test tool initializes correctly"""
        assert translation_tool is not None
        metadata = translation_tool.get_metadata()
        assert metadata.name == "translation"
        assert metadata.max_input_length == 500000
        assert metadata.supports_streaming is False

    @pytest.mark.asyncio
    async def test_empty_text_handling(self, translation_tool):
        """Test handling of empty text input"""
        result = await translation_tool.execute({"text": ""})
        assert result == {"translated_text": "", "source_language": "unknown"}

    @pytest.mark.asyncio
    async def test_short_text_translation(self, translation_tool):
        """Test translation of short text (no chunking)"""
        text = "Hola mundo"

        translation_tool.llm_client.chat.completions.create = AsyncMock(
            return_value=Mock(
                choices=[Mock(message=Mock(content='Hello world'))]
            )
        )

        result = await translation_tool.execute({
            "text": text,
            "source_language": "es"
        })

        assert result["translated_text"] == "Hello world"
        assert result["source_language"] == "es"

    @pytest.mark.asyncio
    async def test_long_text_chunking(self, translation_tool):
        """Test translation with long text requiring chunking"""
        # Create text longer than 40,000 characters
        base_text = "Hola mundo. " * 100
        long_text = base_text * 35  # ~42,000 characters

        translation_tool.llm_client.chat.completions.create = AsyncMock(
            return_value=Mock(
                choices=[Mock(message=Mock(content='Hello world.'))]
            )
        )

        result = await translation_tool.execute({
            "text": long_text,
            "source_language": "es"
        })

        assert "translated_text" in result
        assert len(result["translated_text"]) > 0
        assert result["source_language"] == "es"

    @pytest.mark.asyncio
    async def test_auto_language_detection(self, translation_tool):
        """Test translation with auto language detection"""
        text = "Bonjour le monde"

        translation_tool.llm_client.chat.completions.create = AsyncMock(
            return_value=Mock(
                choices=[Mock(message=Mock(content='Hello world'))]
            )
        )

        result = await translation_tool.execute({"text": text})

        assert result["translated_text"] == "Hello world"
        assert result["source_language"] == "auto"

    @pytest.mark.asyncio
    async def test_fallback_without_llm(self, translation_tool):
        """Test fallback translation without LLM client"""
        translation_tool.llm_client = None

        text = "Hola mundo"

        result = await translation_tool.execute({"text": text})

        # Should return original text when no LLM
        assert result["translated_text"] == text

    @pytest.mark.asyncio
    async def test_response_parsing(self, translation_tool):
        """Test parsing of translation response with common prefixes"""
        text = "Test"

        # Test with "English translation:" prefix
        translation_tool.llm_client.chat.completions.create = AsyncMock(
            return_value=Mock(
                choices=[Mock(message=Mock(content='English translation: This is the result'))]
            )
        )

        result = await translation_tool.execute({"text": text})
        assert result["translated_text"] == "This is the result"

    @pytest.mark.asyncio
    async def test_preserves_formatting(self, translation_tool):
        """Test that translation preserves formatting"""
        text = "Título\n\nPárrafo uno.\n\nPárrafo dos."

        translation_tool.llm_client.chat.completions.create = AsyncMock(
            return_value=Mock(
                choices=[Mock(message=Mock(content='Title\n\nParagraph one.\n\nParagraph two.'))]
            )
        )

        result = await translation_tool.execute({"text": text})

        # Check that newlines are preserved
        assert "\n\n" in result["translated_text"]
