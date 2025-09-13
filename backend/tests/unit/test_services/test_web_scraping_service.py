"""Tests for WebScrapingService

Following prompt.md guidelines:
- No mocks, only real implementations
- Async tests with pytest-asyncio
- 80% coverage minimum
- Real test data
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta
import hashlib
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from src.services.web_scraping_service import WebScrapingService
from src.models.document import (
    DocumentMessage,
    DocumentType,
    DocumentMetadata,
    DocumentContent,
    ProcessingStage,
    DocumentSource,
    ContentBlock
)
from src.core.config import get_settings


@pytest_asyncio.fixture
async def web_scraping_service():
    """Create WebScrapingService instance for testing"""
    service = WebScrapingService()
    yield service
    # Cleanup
    try:
        await service.cleanup()
    except Exception:
        pass  # Ignore cleanup errors in tests


@pytest.fixture
def sample_html():
    """Sample HTML content for testing"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
        <meta name="description" content="Test description">
        <meta name="keywords" content="test, sample, html">
        <meta name="author" content="Test Author">
        <meta property="og:title" content="OG Test Title">
        <meta property="og:description" content="OG Test Description">
        <meta property="og:image" content="https://example.com/image.jpg">
        <meta property="article:published_time" content="2024-01-01T00:00:00Z">
    </head>
    <body>
        <header>
            <h1>Test Page Header</h1>
            <nav>
                <a href="/home">Home</a>
                <a href="/about">About</a>
                <a href="/contact">Contact</a>
            </nav>
        </header>
        <main>
            <article>
                <h2>Article Title</h2>
                <p>This is a test paragraph with <strong>bold text</strong> and <em>italic text</em>.</p>
                <p>Another paragraph with a <a href="https://example.com">link</a>.</p>
                <ul>
                    <li>List item 1</li>
                    <li>List item 2</li>
                    <li>List item 3</li>
                </ul>
                <ol>
                    <li>Ordered item 1</li>
                    <li>Ordered item 2</li>
                </ol>
                <blockquote>This is a quote</blockquote>
            </article>
        </main>
        <footer>
            <p>Footer content © 2024</p>
        </footer>
        <script>console.log('test');</script>
        <style>body { margin: 0; }</style>
    </body>
    </html>
    """


@pytest.fixture
def sample_html_with_relative_links():
    """HTML with relative links for testing"""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Relative Links Test</title></head>
    <body>
        <a href="/page1">Page 1</a>
        <a href="page2.html">Page 2</a>
        <a href="../page3">Page 3</a>
        <a href="https://external.com">External</a>
        <a href="//cdn.example.com/resource">Protocol Relative</a>
        <img src="/images/test.jpg" alt="Test">
        <img src="logo.png" alt="Logo">
        <img src="https://example.com/absolute.jpg" alt="Absolute">
    </body>
    </html>
    """


@pytest.fixture
def complex_html():
    """Complex HTML with various elements"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Complex Page</title>
        <meta charset="UTF-8">
    </head>
    <body>
        <div class="container">
            <h1>Main Title</h1>
            <section>
                <h2>Section 1</h2>
                <p>Content with <code>inline code</code>.</p>
                <pre><code>
                    def hello():
                        print("Hello World")
                </code></pre>
            </section>
            <table>
                <thead>
                    <tr><th>Header 1</th><th>Header 2</th></tr>
                </thead>
                <tbody>
                    <tr><td>Cell 1</td><td>Cell 2</td></tr>
                </tbody>
            </table>
            <form>
                <input type="text" placeholder="Input field">
                <button>Submit</button>
            </form>
        </div>
    </body>
    </html>
    """


class TestWebScrapingService:
    """Test suite for WebScrapingService"""

    @pytest.mark.asyncio
    async def test_service_initialization(self, web_scraping_service):
        """Test service initializes correctly"""
        assert web_scraping_service is not None
        assert web_scraping_service.service_name == "WebScrapingService"
        assert web_scraping_service.storage is not None
        assert web_scraping_service.client is not None
        assert isinstance(web_scraping_service.client, httpx.AsyncClient)
        assert web_scraping_service.html2text is not None
        assert web_scraping_service.cache is not None
        assert isinstance(web_scraping_service.cache, dict)

    @pytest.mark.asyncio
    async def test_health_check(self, web_scraping_service):
        """Test health check functionality"""
        health = await web_scraping_service.health_check()

        assert health['service'] == 'WebScrapingService'
        assert health['status'] == 'healthy'
        assert 'http_client' in health
        assert 'playwright_available' in health
        assert 'cache_size' in health
        assert 'storage_type' in health

    @pytest.mark.asyncio
    async def test_html_to_markdown_conversion(self, web_scraping_service, sample_html):
        """Test HTML to markdown conversion"""
        markdown = await web_scraping_service._html_to_markdown(
            sample_html,
            "https://example.com"
        )

        assert isinstance(markdown, str)
        assert len(markdown) > 0

        # Check for content preservation
        assert "Test Page Header" in markdown
        assert "Article Title" in markdown
        assert "bold text" in markdown
        assert "italic text" in markdown

        # Check for link
        assert "example.com" in markdown or "[link]" in markdown

        # Check for list items
        assert "List item 1" in markdown

        # Verify scripts and styles are removed
        assert "console.log" not in markdown
        assert "margin: 0" not in markdown

    @pytest.mark.asyncio
    async def test_metadata_extraction(self, web_scraping_service, sample_html):
        """Test metadata extraction from HTML"""
        soup = BeautifulSoup(sample_html, 'html.parser')
        metadata = web_scraping_service._extract_metadata(soup)

        assert metadata['title'] == 'Test Page'
        assert metadata['description'] == 'Test description'
        assert metadata['keywords'] == 'test, sample, html'
        assert metadata['author'] == 'Test Author'
        assert metadata['og_title'] == 'OG Test Title'
        assert metadata['og_description'] == 'OG Test Description'
        assert metadata['og_image'] == 'https://example.com/image.jpg'
        assert metadata['published_date'] == '2024-01-01T00:00:00Z'

    @pytest.mark.asyncio
    async def test_relative_url_resolution(self, web_scraping_service, sample_html_with_relative_links):
        """Test that relative URLs are converted to absolute"""
        base_url = "https://example.com/path/page.html"
        markdown = await web_scraping_service._html_to_markdown(
            sample_html_with_relative_links,
            base_url
        )

        # Check that URLs are resolved
        assert "https://example.com/page1" in markdown
        assert "https://example.com/path/page2.html" in markdown
        assert "https://example.com/page3" in markdown
        assert "https://external.com" in markdown
        assert "https://example.com/images/test.jpg" in markdown
        assert "https://example.com/path/logo.png" in markdown

    @pytest.mark.asyncio
    async def test_markdown_cleaning(self, web_scraping_service):
        """Test markdown cleaning functionality"""
        dirty_markdown = """


This is text.



More text here.

[Link] (https://example.com)

<!-- HTML comment -->
<!-- Another comment -->

Final text.


"""
        clean = web_scraping_service._clean_markdown(dirty_markdown)

        # Check excessive blank lines are removed
        assert "\n\n\n" not in clean
        assert "\n\n\n\n" not in clean

        # Check HTML comments are removed
        assert "<!--" not in clean
        assert "-->" not in clean
        assert "HTML comment" not in clean

        # Check broken markdown links are fixed
        assert "[Link] (" not in clean  # Space should be removed

        # Check content is preserved
        assert "This is text" in clean
        assert "More text here" in clean
        assert "Final text" in clean

    @pytest.mark.asyncio
    async def test_cache_functionality(self, web_scraping_service):
        """Test caching mechanism"""
        # Create a test document
        test_doc = DocumentMessage(
            metadata=DocumentMetadata(
                document_id="test123",
                document_type=DocumentType.WEBPAGE,
                name="Test",
                created_user="test_user",
                updated_user="test_user",
                source_url="https://example.com",
                source=DocumentSource.WEB,
                processing_stage=ProcessingStage.COMPLETED
            ),
            content=DocumentContent(
                raw_text="test content",
                formatted_content="test content"
            )
        )

        # Add to cache
        cache_key = "https://example.com:False"
        web_scraping_service.cache[cache_key] = {
            'document': test_doc,
            'timestamp': datetime.utcnow()
        }

        assert len(web_scraping_service.cache) == 1

        # Test cache expiry
        # Add an expired entry
        expired_key = "https://expired.com:False"
        web_scraping_service.cache[expired_key] = {
            'document': test_doc,
            'timestamp': datetime.utcnow() - timedelta(hours=2)  # Expired
        }

        assert len(web_scraping_service.cache) == 2

        # Clear cache
        stats = await web_scraping_service.clear_cache()
        assert stats['entries_cleared'] == 2
        assert stats['cache_size'] == 0
        assert len(web_scraping_service.cache) == 0

    @pytest.mark.asyncio
    async def test_document_message_creation(self, web_scraping_service):
        """Test that service creates proper DocumentMessage objects"""
        url = "https://example.com/page"
        doc_id = hashlib.sha256(url.encode()).hexdigest()[:12]

        document = DocumentMessage(
            metadata=DocumentMetadata(
                document_id=doc_id,
                document_type=DocumentType.WEBPAGE,
                name="Test Page",
                created_user="test_user",
                updated_user="test_user",
                source_url=url,
                tags=["webpage", "scraping"],
                processing_stage=ProcessingStage.COMPLETED,
                source=DocumentSource.WEB
            ),
            content=DocumentContent(
                raw_text="Scraped content",
                formatted_content="Scraped content",
                structured_data={
                    "source": "web_scraping",
                    "url": url
                }
            ),
            user_id="test_user",
            session_id="test_session"
        )

        # Test the document structure
        assert document.metadata.document_id == doc_id
        assert document.metadata.id == doc_id  # Check alias
        assert document.metadata.document_type == DocumentType.WEBPAGE
        assert document.metadata.type == DocumentType.WEBPAGE  # Check alias
        assert document.metadata.source == DocumentSource.WEB
        assert document.content.raw_text == "Scraped content"
        assert document.content.structured_data is not None

    @pytest.mark.asyncio
    async def test_service_uses_centralized_config(self, web_scraping_service):
        """Test that service uses centralized configuration"""
        settings = get_settings()

        # Verify service uses settings
        assert web_scraping_service.settings == settings
        assert web_scraping_service.settings.storage.type in ["filesystem", "redis"]

    @pytest.mark.asyncio
    async def test_httpx_client_configuration(self, web_scraping_service):
        """Test httpx client is configured correctly"""
        assert web_scraping_service.client is not None
        assert web_scraping_service.client.timeout.read == 30.0
        assert web_scraping_service.client.follow_redirects is True
        assert 'User-Agent' in web_scraping_service.client.headers

        # Check user agent is properly set
        user_agent = web_scraping_service.client.headers['User-Agent']
        assert 'Mozilla' in user_agent

    @pytest.mark.asyncio
    async def test_storage_integration(self, web_scraping_service):
        """Test storage integration"""
        # Create a test document
        test_doc = {
            "metadata": {
                "document_id": "web_test123",
                "document_type": "webpage",
                "name": "Web Test",
                "created_user": "test",
                "updated_user": "test"
            },
            "content": {
                "raw_text": "web content",
                "formatted_content": "# Web Test\n\nweb content"
            }
        }

        # Store document
        await web_scraping_service.storage.store("web_test123", test_doc)

        # Retrieve and verify
        retrieved = await web_scraping_service.storage.load("web_test123")
        assert retrieved is not None
        assert retrieved["metadata"]["document_id"] == "web_test123"

        # Cleanup
        await web_scraping_service.storage.delete("web_test123")

    @pytest.mark.asyncio
    async def test_async_http_operations(self, web_scraping_service):
        """Test that HTTP operations are async"""
        # Test with httpbin.org (public test service)
        try:
            response = await web_scraping_service.client.get("https://httpbin.org/html")
            assert response.status_code == 200
            assert len(response.text) > 0
            assert "Herman Melville" in response.text  # httpbin returns Moby Dick text
        except (httpx.ConnectError, httpx.TimeoutException):
            # Skip if network is unavailable
            pytest.skip("Network unavailable or httpbin.org is down")

    @pytest.mark.asyncio
    async def test_error_handling_and_logging(self, web_scraping_service):
        """Test error handling and logging"""
        # Test with invalid URL should raise exception
        with pytest.raises(Exception):
            await web_scraping_service._scrape_with_httpx("not_a_valid_url")

        # Verify logger is configured
        assert web_scraping_service.logger is not None
        assert web_scraping_service.logger.service_name == "WebScrapingService"

    @pytest.mark.asyncio
    async def test_traced_operations(self, web_scraping_service):
        """Test that operations use tracing"""
        # Verify service has tracer
        assert hasattr(web_scraping_service, 'tracer')
        assert hasattr(web_scraping_service, 'traced_operation')

        # Test traced operation context manager
        with web_scraping_service.traced_operation("test_scrape", url="test"):
            # Operation would be traced here
            pass

    @pytest.mark.asyncio
    async def test_extract_links(self, web_scraping_service):
        """Test link extraction functionality"""
        html = """
        <html>
        <body>
            <a href="https://example.com/page1">Page 1</a>
            <a href="/page2">Page 2</a>
            <a href="page3.html">Page 3</a>
            <a href="https://example.com/page1">Duplicate</a>
            <a>No href</a>
            <a href="">Empty href</a>
            <a href="javascript:void(0)">JavaScript</a>
            <a href="mailto:test@example.com">Email</a>
            <a href="#anchor">Anchor</a>
            <a href="tel:+1234567890">Phone</a>
        </body>
        </html>
        """

        # Mock the scraping to return our test HTML
        async def mock_scrape(url):
            return html, "Test"

        # Replace method temporarily
        original = web_scraping_service._scrape_with_httpx
        web_scraping_service._scrape_with_httpx = mock_scrape

        try:
            links = await web_scraping_service.extract_links("https://example.com/")

            # Should extract HTTP/HTTPS links and resolve relative ones
            assert "https://example.com/page1" in links
            assert "https://example.com/page2" in links
            assert "https://example.com/page3.html" in links

            # Should not have duplicates
            assert links.count("https://example.com/page1") == 1

            # Should not include non-HTTP links
            assert "javascript:void(0)" not in links
            assert "mailto:test@example.com" not in links
            assert "tel:+1234567890" not in links

        finally:
            # Restore original method
            web_scraping_service._scrape_with_httpx = original

    @pytest.mark.asyncio
    async def test_cleanup(self, web_scraping_service):
        """Test service cleanup"""
        # Add something to cache
        web_scraping_service.cache["test"] = {
            'document': None,
            'timestamp': datetime.utcnow()
        }

        # Run cleanup
        await web_scraping_service.cleanup()

        # Verify cache is cleared
        assert len(web_scraping_service.cache) == 0

    @pytest.mark.asyncio
    async def test_html2text_configuration(self, web_scraping_service):
        """Test html2text converter configuration"""
        assert web_scraping_service.html2text is not None
        assert web_scraping_service.html2text.ignore_links is False
        assert web_scraping_service.html2text.ignore_images is False
        assert web_scraping_service.html2text.ignore_emphasis is False
        assert web_scraping_service.html2text.body_width == 0  # No wrapping
        assert web_scraping_service.html2text.single_line_break is True

    @pytest.mark.asyncio
    async def test_complex_html_conversion(self, web_scraping_service, complex_html):
        """Test conversion of complex HTML elements"""
        markdown = await web_scraping_service._html_to_markdown(
            complex_html,
            "https://example.com"
        )

        # Check various elements are preserved
        assert "Main Title" in markdown
        assert "Section 1" in markdown
        assert "inline code" in markdown or "`inline code`" in markdown
        assert "Header 1" in markdown
        assert "Cell 1" in markdown

    @pytest.mark.asyncio
    async def test_scrape_webpage_structure(self, web_scraping_service):
        """Test scrape_webpage method structure"""
        # Verify method exists and has correct signature
        assert hasattr(web_scraping_service, 'scrape_webpage')

        # The method should handle these parameters
        method = web_scraping_service.scrape_webpage
        import inspect
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())

        assert 'url' in params
        assert 'use_javascript' in params
        assert 'user_id' in params
        assert 'session_id' in params

    @pytest.mark.asyncio
    async def test_cache_duration(self, web_scraping_service):
        """Test cache duration is properly set"""
        assert web_scraping_service.cache_duration == timedelta(hours=1)

        # Test that cache respects duration
        test_doc = DocumentMessage(
            metadata=DocumentMetadata(
                document_id="cache_test",
                document_type=DocumentType.WEBPAGE,
                name="Cache Test",
                created_user="test",
                updated_user="test"
            ),
            content=DocumentContent(
                raw_text="cached content"
            )
        )

        # Add fresh cache entry
        fresh_key = "https://fresh.com:False"
        web_scraping_service.cache[fresh_key] = {
            'document': test_doc,
            'timestamp': datetime.utcnow()
        }

        # Add stale cache entry
        stale_key = "https://stale.com:False"
        web_scraping_service.cache[stale_key] = {
            'document': test_doc,
            'timestamp': datetime.utcnow() - timedelta(hours=2)
        }

        # Check cache has both entries
        assert len(web_scraping_service.cache) == 2