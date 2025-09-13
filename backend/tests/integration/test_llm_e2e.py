"""End-to-end tests for LLM Service with Claude and OpenAI"""

import pytest
import os
import asyncio
from typing import Optional

from src.services.llm_service import LLMService, LLMProvider, Entity
from src.core.config import get_settings


class TestLLME2E:
    """End-to-end tests for actual LLM API calls"""

    @pytest.fixture
    def has_openai_key(self) -> bool:
        """Check if OpenAI API key is available"""
        settings = get_settings()
        return bool(settings.llm.openai_api_key)

    @pytest.fixture
    def has_anthropic_key(self) -> bool:
        """Check if Anthropic API key is available"""
        settings = get_settings()
        return bool(settings.llm.anthropic_api_key)

    @pytest.fixture
    def openai_service(self) -> Optional[LLMService]:
        """Create OpenAI LLM service if API key is available"""
        settings = get_settings()
        if settings.llm.openai_api_key:
            return LLMService(provider=LLMProvider.OPENAI)
        return None

    @pytest.fixture
    def anthropic_service(self) -> Optional[LLMService]:
        """Create Anthropic LLM service if API key is available"""
        settings = get_settings()
        if settings.llm.anthropic_api_key:
            return LLMService(provider=LLMProvider.ANTHROPIC)
        return None

    @pytest.fixture
    def sample_text(self) -> str:
        """Sample text for testing"""
        return """
        Apple Inc. announced its quarterly earnings on January 15, 2024.
        The company, led by CEO Tim Cook, reported revenue of $120 billion.
        The iPhone 15 Pro Max has been a major success in the market.
        Apple's headquarters in Cupertino, California continues to be a hub of innovation.
        """

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("LLM__OPENAI_API_KEY"),
        reason="OpenAI API key not configured"
    )
    async def test_openai_summarization(self, openai_service, sample_text):
        """Test OpenAI summarization"""
        if not openai_service:
            pytest.skip("OpenAI service not available")

        summary = await openai_service.generate_summary(
            sample_text,
            max_length=100,
            style="concise"
        )

        assert summary is not None
        assert len(summary) > 10  # Should have actual content
        assert "Apple" in summary or "company" in summary.lower()

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("LLM__ANTHROPIC_API_KEY"),
        reason="Anthropic API key not configured"
    )
    async def test_claude_summarization(self, anthropic_service, sample_text):
        """Test Claude summarization"""
        if not anthropic_service:
            pytest.skip("Anthropic service not available")

        summary = await anthropic_service.generate_summary(
            sample_text,
            max_length=100,
            style="concise"
        )

        assert summary is not None
        assert len(summary) > 10  # Should have actual content
        assert "Apple" in summary or "company" in summary.lower()

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("LLM__OPENAI_API_KEY"),
        reason="OpenAI API key not configured"
    )
    async def test_openai_entity_extraction(self, openai_service, sample_text):
        """Test OpenAI entity extraction"""
        if not openai_service:
            pytest.skip("OpenAI service not available")

        entities = await openai_service.extract_entities(sample_text)

        assert entities is not None
        assert len(entities) > 0
        assert any(e.text == "Apple Inc." or "Apple" in e.text for e in entities)
        assert any(e.text == "Tim Cook" or "Cook" in e.text for e in entities)

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("LLM__ANTHROPIC_API_KEY"),
        reason="Anthropic API key not configured"
    )
    async def test_claude_entity_extraction(self, anthropic_service, sample_text):
        """Test Claude entity extraction"""
        if not anthropic_service:
            pytest.skip("Anthropic service not available")

        entities = await anthropic_service.extract_entities(sample_text)

        assert entities is not None
        assert len(entities) > 0
        assert any(e.text == "Apple Inc." or "Apple" in e.text for e in entities)
        assert any(e.text == "Tim Cook" or "Cook" in e.text for e in entities)

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("LLM__OPENAI_API_KEY"),
        reason="OpenAI API key not configured"
    )
    async def test_openai_classification(self, openai_service, sample_text):
        """Test OpenAI document classification"""
        if not openai_service:
            pytest.skip("OpenAI service not available")

        categories = ["Technology", "Finance", "Healthcare", "Education"]
        category, confidence = await openai_service.classify_document(
            sample_text,
            categories
        )

        assert category in categories
        assert 0.0 <= confidence <= 1.0
        assert category in ["Technology", "Finance"]  # Should classify as tech or finance

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("LLM__ANTHROPIC_API_KEY"),
        reason="Anthropic API key not configured"
    )
    async def test_claude_classification(self, anthropic_service, sample_text):
        """Test Claude document classification"""
        if not anthropic_service:
            pytest.skip("Anthropic service not available")

        categories = ["Technology", "Finance", "Healthcare", "Education"]
        category, confidence = await anthropic_service.classify_document(
            sample_text,
            categories
        )

        assert category in categories
        assert 0.0 <= confidence <= 1.0
        assert category in ["Technology", "Finance"]  # Should classify as tech or finance

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("LLM__OPENAI_API_KEY"),
        reason="OpenAI API key not configured"
    )
    async def test_openai_question_answering(self, openai_service, sample_text):
        """Test OpenAI question answering"""
        if not openai_service:
            pytest.skip("OpenAI service not available")

        question = "Who is the CEO of Apple?"
        answer = await openai_service.answer_question(
            sample_text,
            question,
            max_length=50
        )

        assert answer is not None
        assert "Tim Cook" in answer or "Cook" in answer

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("LLM__ANTHROPIC_API_KEY"),
        reason="Anthropic API key not configured"
    )
    async def test_claude_question_answering(self, anthropic_service, sample_text):
        """Test Claude question answering"""
        if not anthropic_service:
            pytest.skip("Anthropic service not available")

        question = "Who is the CEO of Apple?"
        answer = await anthropic_service.answer_question(
            sample_text,
            question,
            max_length=50
        )

        assert answer is not None
        assert "Tim Cook" in answer or "Cook" in answer

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("LLM__OPENAI_API_KEY"),
        reason="OpenAI API key not configured"
    )
    async def test_openai_embeddings(self, openai_service, sample_text):
        """Test OpenAI embeddings generation"""
        if not openai_service:
            pytest.skip("OpenAI service not available")

        embeddings = await openai_service.generate_embeddings(sample_text)

        assert embeddings is not None
        assert len(embeddings) > 0
        assert all(isinstance(e, float) for e in embeddings)
        # OpenAI ada-002 embeddings should be 1536 dimensions
        assert len(embeddings) == 1536

    @pytest.mark.asyncio
    async def test_provider_switching(self, sample_text):
        """Test switching between providers"""
        settings = get_settings()

        # Test with each available provider
        if settings.llm.openai_api_key:
            openai_service = LLMService(provider=LLMProvider.OPENAI)
            summary = await openai_service.generate_summary(sample_text, max_length=50)
            assert summary is not None
            assert openai_service.provider == LLMProvider.OPENAI

        if settings.llm.anthropic_api_key:
            anthropic_service = LLMService(provider=LLMProvider.ANTHROPIC)
            summary = await anthropic_service.generate_summary(sample_text, max_length=50)
            assert summary is not None
            assert anthropic_service.provider == LLMProvider.ANTHROPIC

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, sample_text):
        """Test concurrent operations with available providers"""
        settings = get_settings()
        services = []

        if settings.llm.openai_api_key:
            services.append(LLMService(provider=LLMProvider.OPENAI))

        if settings.llm.anthropic_api_key:
            services.append(LLMService(provider=LLMProvider.ANTHROPIC))

        if not services:
            pytest.skip("No LLM services available")

        # Run operations concurrently
        service = services[0]
        results = await asyncio.gather(
            service.generate_summary(sample_text, max_length=100),
            service.extract_entities(sample_text),
            service.classify_document(sample_text),
            return_exceptions=True
        )

        # Check all operations succeeded
        for result in results:
            assert not isinstance(result, Exception)

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling with invalid inputs"""
        settings = get_settings()

        if settings.llm.openai_api_key:
            service = LLMService(provider=LLMProvider.OPENAI)
        elif settings.llm.anthropic_api_key:
            service = LLMService(provider=LLMProvider.ANTHROPIC)
        else:
            pytest.skip("No LLM services available")

        # Test with empty text
        summary = await service.generate_summary("", max_length=100)
        assert summary == "No text provided for summarization."

        # Test with empty question
        answer = await service.answer_question("Some text", "")
        assert answer == "Insufficient information provided."

        # Test with empty context
        answer = await service.answer_question("", "What is this?")
        assert answer == "Insufficient information provided."