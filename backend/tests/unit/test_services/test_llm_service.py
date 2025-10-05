"""Tests for LLMService"""

import pytest
from typing import List

from src.services.llm_service import LLMService, LLMProvider
from src.models.document import DocumentMessage, DocumentMetadata, DocumentContent, DocumentType


class TestLLMService:
    """Test suite for LLMService"""

    @pytest.fixture
    def service(self):
        """Create an LLMService instance for testing"""
        return LLMService(provider=LLMProvider.OPENAI)

    @pytest.fixture
    def sample_text(self):
        """Sample text for testing"""
        return """
        Apple Inc. announced its quarterly earnings on January 15, 2024.
        The company, led by CEO Tim Cook, reported revenue of $120 billion.
        The event took place at their headquarters in Cupertino, California.
        For more information, contact press@apple.com or call 1-800-APPLE.
        """

    @pytest.fixture
    def test_document(self) -> DocumentMessage:
        """Create a test document for AI processing"""
        metadata = DocumentMetadata(
            document_id="test-doc-ai",
            document_type=DocumentType.MARKDOWN,
            name="AI Test Document",
            created_user="test_user",
            updated_user="test_user"
        )

        content = DocumentContent(
            formatted_content="# Test Document\n\nThis is a test document for AI processing.",
            raw_text="Test Document. This is a test document for AI processing."
        )

        return DocumentMessage(
            metadata=metadata,
            content=content,
            tools=[],
            user_id="test_user"
        )

    def test_initialization(self):
        """Test service initialization with different providers"""
        # Test with OpenAI
        service_openai = LLMService(provider=LLMProvider.OPENAI)
        assert service_openai.provider == LLMProvider.OPENAI

        # Test with Anthropic
        service_anthropic = LLMService(provider=LLMProvider.ANTHROPIC)
        assert service_anthropic.provider == LLMProvider.ANTHROPIC

    @pytest.mark.asyncio
    async def test_generate_summary(self, service, sample_text):
        """Test text summarization"""
        # Test concise summary
        summary = await service.generate_summary(sample_text, max_length=100, style="concise")
        assert summary is not None
        assert isinstance(summary, str)
        assert len(summary) > 0

        # Test detailed summary
        detailed = await service.generate_summary(sample_text, max_length=200, style="detailed")
        assert detailed is not None

        # Test bullet points summary
        bullets = await service.generate_summary(sample_text, max_length=150, style="bullet_points")
        assert bullets is not None

    @pytest.mark.asyncio
    async def test_generate_summary_empty_text(self, service):
        """Test summarization with empty text"""
        summary = await service.generate_summary("", max_length=100)
        assert summary == "No text provided for summarization."

        summary = await service.generate_summary("   ", max_length=100)
        assert summary == "No text provided for summarization."

    @pytest.mark.asyncio
    async def test_extract_entities(self, service, sample_text):
        """Test entity extraction"""
        entities = await service.extract_entities(sample_text)

        assert entities is not None
        assert isinstance(entities, list)
        assert len(entities) > 0
        assert all(isinstance(e, dict) for e in entities)

        # Check entity structure
        if entities:
            entity = entities[0]
            assert 'text' in entity
            assert 'entity_type' in entity
            assert 'confidence' in entity

    @pytest.mark.asyncio
    async def test_extract_entities_with_types(self, service, sample_text):
        """Test entity extraction with specific types"""
        entity_types = ["PERSON", "ORGANIZATION", "LOCATION"]
        entities = await service.extract_entities(sample_text, entity_types)

        assert entities is not None
        assert isinstance(entities, list)

    @pytest.mark.asyncio
    async def test_extract_entities_empty_text(self, service):
        """Test entity extraction with empty text"""
        entities = await service.extract_entities("")
        assert entities == []

    def test_entity_dict_structure(self):
        """Test entity dictionary structure"""
        # Entities are now returned as dictionaries directly
        entity_dict = {
            "text": "Apple Inc.",
            "entity_type": "ORGANIZATION",
            "confidence": 0.95,
            "metadata": {"source": "test"}
        }

        assert entity_dict["text"] == "Apple Inc."
        assert entity_dict["entity_type"] == "ORGANIZATION"
        assert entity_dict["confidence"] == 0.95
        assert entity_dict["metadata"]["source"] == "test"

    @pytest.mark.asyncio
    async def test_classify_document(self, service, sample_text):
        """Test document classification"""
        category, confidence = await service.classify_document(sample_text)

        assert category is not None
        assert isinstance(category, str)
        assert confidence is not None
        assert 0.0 <= confidence <= 1.0

    @pytest.mark.asyncio
    async def test_classify_document_with_categories(self, service, sample_text):
        """Test classification with custom categories"""
        categories = ["Technology", "Finance", "Healthcare", "Education"]
        category, confidence = await service.classify_document(sample_text, categories)

        assert category is not None
        assert confidence is not None

    @pytest.mark.asyncio
    async def test_classify_document_empty_text(self, service):
        """Test classification with empty text"""
        category, confidence = await service.classify_document("")
        assert category == "UNKNOWN"
        assert confidence == 0.0

    @pytest.mark.asyncio
    async def test_answer_question(self, service, sample_text):
        """Test question answering"""
        question = "Who is the CEO mentioned in the text?"
        answer = await service.answer_question(sample_text, question, max_length=50)

        assert answer is not None
        assert isinstance(answer, str)
        assert len(answer) > 0

    @pytest.mark.asyncio
    async def test_answer_question_empty_inputs(self, service):
        """Test Q&A with empty inputs"""
        # Empty context
        answer = await service.answer_question("", "What is this?")
        assert answer == "Insufficient information provided."

        # Empty question
        answer = await service.answer_question("Some context", "")
        assert answer == "Insufficient information provided."

    @pytest.mark.asyncio
    async def test_generate_embeddings(self, service, sample_text):
        """Test embedding generation"""
        embeddings = await service.generate_embeddings(sample_text)

        assert embeddings is not None
        assert isinstance(embeddings, list)
        assert len(embeddings) > 0
        assert all(isinstance(e, float) for e in embeddings)

    @pytest.mark.asyncio
    async def test_process_document_with_ai(self, service, test_document):
        """Test processing document with multiple AI operations"""
        operations = ["summary", "entities", "classify", "embeddings"]

        processed = await service.process_document_with_ai(test_document, operations)

        assert processed is not None
        assert processed.metadata.summary is not None
        assert processed.content.structured_data is not None
        assert "entities" in processed.content.structured_data
        assert "classification" in processed.content.structured_data
        assert processed.content.embeddings is not None
        assert all(f"llm_{op}" in processed.tools for op in operations)

    @pytest.mark.asyncio
    async def test_process_document_partial_operations(self, service, test_document):
        """Test processing document with subset of operations"""
        operations = ["summary", "classify"]

        processed = await service.process_document_with_ai(test_document, operations)

        assert processed.metadata.summary is not None
        assert "classification" in processed.content.structured_data
        assert "llm_summary" in processed.tools
        assert "llm_classify" in processed.tools

    @pytest.mark.skip(reason="Private methods removed in refactoring - now handled by tools")
    def test_prepare_summary_prompt(self, service):
        """Test prompt preparation for summarization"""
        pass  # This is now handled internally by SummarizationTool

    @pytest.mark.skip(reason="Private methods removed in refactoring - now handled by tools")
    def test_parse_entities(self, service):
        """Test entity parsing from LLM response"""
        pass  # This is now handled internally by EntityExtractionTool

    @pytest.mark.skip(reason="Private methods removed in refactoring - now handled by tools")
    def test_parse_classification(self, service):
        """Test classification parsing from LLM response"""
        pass  # This is now handled internally by ClassificationTool

    @pytest.mark.asyncio
    async def test_health_check(self, service):
        """Test service health check"""
        health = await service.health_check()

        assert health["service"] == "LLMService"
        assert health["status"] in ["healthy", "degraded"]
        assert health["provider"] == "openai"
        assert "capabilities" in health
        assert "summarization" in health["capabilities"]
        assert "configuration" in health
        # OpenAI service should have OpenAI-specific settings
        assert health["configuration"]["max_tokens"] == 2000  # OpenAI max_tokens
        assert health["configuration"]["temperature"] == 0.3  # OpenAI temperature

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, service, sample_text):
        """Test concurrent LLM operations"""
        import asyncio

        # Run multiple operations concurrently
        results = await asyncio.gather(
            service.generate_summary(sample_text, max_length=100),
            service.extract_entities(sample_text),
            service.classify_document(sample_text),
            return_exceptions=True
        )

        # All should succeed
        assert all(not isinstance(r, Exception) for r in results)
        assert results[0] is not None  # summary
        assert isinstance(results[1], list)  # entities
        assert isinstance(results[2], tuple)  # (category, confidence)