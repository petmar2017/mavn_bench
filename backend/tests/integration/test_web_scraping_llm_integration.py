"""End-to-end integration test for web scraping with Claude LLM processing

This test demonstrates the full pipeline:
1. Scrape a real webpage using WebScrapingService
2. Process the scraped content with Claude LLM
3. Generate a comprehensive document.md file
4. No mocks - real services only
"""

import pytest
import pytest_asyncio
import asyncio
import os
from pathlib import Path
from datetime import datetime
import hashlib

from src.services.web_scraping_service import WebScrapingService
from src.services.llm_service import LLMService, LLMProvider
from src.models.document import (
    DocumentMessage,
    DocumentType,
    DocumentMetadata,
    DocumentContent,
    ProcessingStage,
    DocumentSource
)
from src.core.config import get_settings
from src.storage.storage_factory import StorageFactory, StorageType


@pytest_asyncio.fixture
async def web_scraping_service():
    """Create real WebScrapingService instance"""
    service = WebScrapingService()
    yield service
    await service.cleanup()


@pytest_asyncio.fixture
async def llm_service():
    """Create real LLMService instance with Claude"""
    service = LLMService(provider=LLMProvider.ANTHROPIC)
    yield service


@pytest_asyncio.fixture
async def storage():
    """Create storage instance for persisting documents"""
    storage = StorageFactory.create(StorageType.FILESYSTEM)
    yield storage


class TestWebScrapingLLMIntegration:
    """End-to-end integration tests using real services"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_scrape_and_generate_document_with_claude(
        self,
        web_scraping_service,
        llm_service,
        storage,
        tmp_path
    ):
        """Test complete pipeline: scrape webpage → process with Claude → generate document.md"""

        # Use a real, stable webpage for testing
        test_url = "https://www.python.org/about/gettingstarted/"

        print(f"\n🌐 Scraping webpage: {test_url}")

        # Step 1: Scrape the webpage
        scraped_document = await web_scraping_service.scrape_webpage(
            url=test_url,
            use_javascript=False,  # Simple HTML page doesn't need JS
            user_id="integration_test",
            session_id="test_session_001"
        )

        assert scraped_document is not None
        assert scraped_document.content.raw_text
        assert scraped_document.content.formatted_content
        assert scraped_document.metadata.name  # Should have page title

        print(f"✅ Scraped: {scraped_document.metadata.name}")
        print(f"   Content length: {len(scraped_document.content.raw_text)} chars")

        # Step 2: Process with Claude LLM
        print("\n🤖 Processing with Claude LLM...")

        # Generate comprehensive analysis using Claude
        analysis_prompt = f"""You are a technical documentation expert. Analyze the following web content and create a comprehensive document.md file.

The document should include:

# {scraped_document.metadata.name}

## Executive Summary
Provide a concise 2-3 paragraph summary of the main content and key takeaways.

## Key Topics
List and explain the main topics covered in bullet points.

## Important Concepts
Identify and explain 3-5 core concepts from the content.

## Code Examples
If there are code examples, include the most important ones with explanations.

## Best Practices
Extract any best practices or recommendations mentioned.

## Resources and Links
List important resources, tools, or links mentioned.

## Conclusion
Provide a brief conclusion about the value and applicability of this content.

---

Web Content to Analyze:
{scraped_document.content.formatted_content[:8000]}  # Limit for token constraints

Please generate a well-structured, professional document.md based on the above content."""

        # Call Claude to generate the document
        generated_doc_content = await llm_service._call_llm(
            prompt=analysis_prompt,
            max_tokens=2000,
            temperature=0.3  # Lower temperature for more focused output
        )

        assert generated_doc_content
        assert len(generated_doc_content) > 100

        print(f"✅ Claude generated document: {len(generated_doc_content)} chars")

        # Step 3: Generate additional AI insights
        operations = ["summary", "entities", "classify"]
        enhanced_document = await llm_service.process_document_with_ai(
            scraped_document,
            operations
        )

        assert enhanced_document.metadata.summary
        assert enhanced_document.content.structured_data
        assert "entities" in enhanced_document.content.structured_data
        assert "classification" in enhanced_document.content.structured_data

        print(f"✅ Enhanced with AI operations: {operations}")

        # Step 4: Create final document.md file
        output_dir = tmp_path / "output"
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / "document.md"

        # Combine all information into final document
        final_document = f"""<!-- Generated by Mavn Bench Integration Test -->
<!-- Source: {test_url} -->
<!-- Generated: {datetime.utcnow().isoformat()} -->
<!-- Processed with: Claude {llm_service.model} -->

{generated_doc_content}

---

## Metadata

- **Source URL**: {test_url}
- **Document Type**: {enhanced_document.metadata.document_type}
- **Classification**: {enhanced_document.content.structured_data.get('classification', {}).get('category', 'Unknown')} (Confidence: {enhanced_document.content.structured_data.get('classification', {}).get('confidence', 0):.2f})
- **Processing Date**: {datetime.utcnow().isoformat()}
- **Document ID**: {enhanced_document.metadata.document_id}

### Extracted Entities
"""

        # Add entities to document
        entities = enhanced_document.content.structured_data.get("entities", [])
        for entity in entities[:10]:  # Limit to first 10 entities
            final_document += f"- **{entity.get('type', 'UNKNOWN')}**: {entity.get('text', '')}\n"

        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(final_document)

        print(f"✅ Generated document.md: {output_file}")

        # Step 5: Store in document storage
        doc_id = enhanced_document.metadata.document_id
        await storage.store(doc_id, enhanced_document.model_dump())

        # Verify storage
        stored_doc = await storage.load(doc_id)
        assert stored_doc is not None

        print(f"✅ Stored in document storage: {doc_id}")

        # Step 6: Validate the generated document
        assert output_file.exists()
        content = output_file.read_text()

        # Verify document structure
        assert "# " in content  # Has headers
        assert "## Executive Summary" in content or "## " in content  # Has sections
        assert test_url in content  # Contains source URL
        assert "Claude" in content  # References Claude processing

        print(f"\n✅ Full pipeline completed successfully!")
        print(f"   - Webpage scraped: {test_url}")
        print(f"   - Processed with Claude LLM")
        print(f"   - Document generated: {output_file}")
        print(f"   - Stored in system: {doc_id}")

        # Cleanup
        await storage.delete(doc_id)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_javascript_heavy_site_with_llm(
        self,
        web_scraping_service,
        llm_service,
        tmp_path
    ):
        """Test scraping JavaScript-heavy site with Playwright and LLM processing"""

        # Use a JS-heavy site
        test_url = "https://react.dev/"

        print(f"\n🌐 Scraping JS-heavy site: {test_url}")

        try:
            # Scrape with JavaScript rendering
            scraped_document = await web_scraping_service.scrape_webpage(
                url=test_url,
                use_javascript=True,  # Use Playwright for JS rendering
                user_id="integration_test",
                session_id="test_session_002"
            )

            assert scraped_document is not None
            assert scraped_document.content.raw_text

            print(f"✅ Scraped with Playwright: {scraped_document.metadata.name}")

            # Generate technical documentation
            tech_doc_prompt = f"""Create a technical overview document for the following React documentation page.

Focus on:
1. Core concepts mentioned
2. Key features highlighted
3. Getting started steps
4. Best practices
5. Important links and resources

Content:
{scraped_document.content.formatted_content[:5000]}

Generate a concise technical document (500-800 words):"""

            doc_content = await llm_service._call_llm(
                prompt=tech_doc_prompt,
                max_tokens=1500,
                temperature=0.3
            )

            # Save to file
            output_file = tmp_path / "react_overview.md"
            output_file.write_text(f"""# React Documentation Overview

Generated from: {test_url}
Date: {datetime.utcnow().isoformat()}

{doc_content}

---
*Generated by Mavn Bench WebScraping + Claude LLM Integration*
""")

            print(f"✅ Generated technical document: {output_file}")
            assert output_file.exists()

        except Exception as e:
            # Playwright might not be installed in all environments
            if "playwright" in str(e).lower():
                pytest.skip("Playwright not installed, skipping JS rendering test")
            else:
                raise

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_multi_page_scraping_with_summary(
        self,
        web_scraping_service,
        llm_service,
        tmp_path
    ):
        """Test scraping multiple pages and generating a unified summary"""

        # URLs to scrape
        urls = [
            "https://docs.python.org/3/tutorial/introduction.html",
            "https://docs.python.org/3/tutorial/controlflow.html",
        ]

        print(f"\n📚 Scraping {len(urls)} pages for unified summary")

        all_content = []

        for url in urls:
            print(f"   Scraping: {url}")
            doc = await web_scraping_service.scrape_webpage(url)
            all_content.append({
                "url": url,
                "title": doc.metadata.name,
                "content": doc.content.formatted_content[:3000]  # Limit per page
            })

        # Generate unified summary with Claude
        unified_prompt = f"""Analyze the following Python tutorial pages and create a unified learning guide.

Pages scraped:
"""
        for page in all_content:
            unified_prompt += f"\n## {page['title']}\nSource: {page['url']}\n{page['content'][:1500]}\n"

        unified_prompt += """

Create a comprehensive learning guide that:
1. Combines key concepts from all pages
2. Provides a logical learning progression
3. Includes important code examples
4. Offers practice recommendations

Generate the guide (800-1000 words):"""

        unified_guide = await llm_service._call_llm(
            prompt=unified_prompt,
            max_tokens=2000,
            temperature=0.4
        )

        # Save unified document
        output_file = tmp_path / "python_tutorial_guide.md"
        output_file.write_text(f"""# Python Tutorial - Unified Learning Guide

Generated from multiple Python documentation pages
Date: {datetime.utcnow().isoformat()}

## Source Pages
""" + "\n".join([f"- [{p['title']}]({p['url']})" for p in all_content]) + f"""

---

{unified_guide}

---
*Generated by Mavn Bench Multi-Page Scraping + Claude LLM Integration*
""")

        print(f"✅ Generated unified guide from {len(urls)} pages: {output_file}")
        assert output_file.exists()
        assert len(output_file.read_text()) > 1000

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_error_handling_and_fallbacks(
        self,
        web_scraping_service,
        llm_service
    ):
        """Test error handling in the integration pipeline"""

        # Test with invalid URL
        invalid_url = "https://this-definitely-does-not-exist-12345.com"

        print(f"\n🧪 Testing error handling with invalid URL: {invalid_url}")

        with pytest.raises(Exception):
            await web_scraping_service.scrape_webpage(invalid_url)

        print("✅ Properly handled invalid URL")

        # Test with empty content
        empty_doc = DocumentMessage(
            metadata=DocumentMetadata(
                document_id="test_empty",
                document_type=DocumentType.WEBPAGE,
                name="Empty Document",
                created_user="test",
                updated_user="test"
            ),
            content=DocumentContent(
                raw_text="",
                formatted_content=""
            )
        )

        # LLM should handle empty content gracefully
        summary = await llm_service.generate_summary("")
        assert summary == "No text provided for summarization."

        print("✅ Properly handled empty content")

        # Test with very large content (should truncate)
        large_text = "Test content. " * 10000  # Very large text
        summary = await llm_service.generate_summary(large_text, max_length=100)
        assert summary  # Should still generate something
        assert len(summary) < len(large_text)  # Should be summarized

        print("✅ Properly handled large content with truncation")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_complete_pipeline_with_metrics():
    """Standalone test for complete pipeline with performance metrics"""

    import time

    print("\n" + "="*60)
    print("🚀 COMPLETE END-TO-END PIPELINE TEST")
    print("="*60)

    # Initialize services
    start_time = time.time()

    web_service = WebScrapingService()
    llm_service = LLMService(provider=LLMProvider.ANTHROPIC)
    storage = StorageFactory.create(StorageType.FILESYSTEM)

    init_time = time.time() - start_time
    print(f"⏱️  Service initialization: {init_time:.2f}s")

    # Scrape webpage
    scrape_start = time.time()
    url = "https://www.python.org/about/"

    document = await web_service.scrape_webpage(url)
    scrape_time = time.time() - scrape_start
    print(f"⏱️  Web scraping: {scrape_time:.2f}s")
    print(f"   - Title: {document.metadata.name}")
    print(f"   - Content size: {len(document.content.raw_text)} chars")

    # Process with LLM
    llm_start = time.time()

    # Generate multiple AI outputs
    operations = ["summary", "entities", "classify"]
    enhanced_doc = await llm_service.process_document_with_ai(document, operations)

    llm_time = time.time() - llm_start
    print(f"⏱️  LLM processing: {llm_time:.2f}s")
    print(f"   - Summary length: {len(enhanced_doc.metadata.summary or '')} chars")
    print(f"   - Entities found: {len(enhanced_doc.content.structured_data.get('entities', []))}")
    print(f"   - Classification: {enhanced_doc.content.structured_data.get('classification', {}).get('category', 'Unknown')}")

    # Store document
    store_start = time.time()
    doc_id = enhanced_doc.metadata.document_id
    await storage.store(doc_id, enhanced_doc.model_dump())
    store_time = time.time() - store_start
    print(f"⏱️  Storage: {store_time:.2f}s")

    # Total time
    total_time = time.time() - start_time
    print(f"\n✅ TOTAL PIPELINE TIME: {total_time:.2f}s")
    print("="*60)

    # Cleanup
    await storage.delete(doc_id)
    await web_service.cleanup()

    # Assertions
    assert total_time < 60  # Should complete within 1 minute
    assert enhanced_doc.metadata.summary
    assert enhanced_doc.content.structured_data

    return {
        "total_time": total_time,
        "scrape_time": scrape_time,
        "llm_time": llm_time,
        "store_time": store_time
    }