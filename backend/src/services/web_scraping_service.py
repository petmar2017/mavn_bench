"""Web scraping service for converting web pages to markdown

This service handles:
- Simple HTML pages with BeautifulSoup4
- JavaScript-heavy sites with Playwright
- Markdown conversion with proper formatting
- Rate limiting and caching
"""

import asyncio
import hashlib
import re
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin

import aiofiles
import httpx
from bs4 import BeautifulSoup, NavigableString, Tag
from playwright.async_api import async_playwright, Browser, Page
import html2text

from .base_service import BaseService
from ..models.document import (
    DocumentMessage,
    DocumentMetadata,
    DocumentContent,
    DocumentType,
    ContentBlock,
    ProcessingStage,
    DocumentSource
)
from ..core.config import get_settings
from ..core.logger import CentralizedLogger
from ..storage.storage_factory import StorageFactory, StorageType


class WebScrapingService(BaseService):
    """Service for scraping web pages and converting to markdown"""

    def __init__(self):
        """Initialize web scraping service"""
        super().__init__("WebScrapingService")
        self.settings = get_settings()
        self.logger = CentralizedLogger("WebScrapingService")

        # Configure storage
        self.storage = StorageFactory.create(
            StorageType(self.settings.storage.type)
        )

        # Configure HTTP client with async support
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                             'AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/120.0.0.0 Safari/537.36'
            }
        )

        # Configure html2text for markdown conversion
        self.html2text = html2text.HTML2Text()
        self.html2text.ignore_links = False
        self.html2text.ignore_images = False
        self.html2text.ignore_emphasis = False
        self.html2text.body_width = 0  # Don't wrap lines
        self.html2text.single_line_break = True

        # Playwright browser instance (initialized on demand)
        self.browser: Optional[Browser] = None

        # Cache for scraped pages (simple in-memory cache)
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_duration = timedelta(hours=1)

    async def health_check(self) -> Dict[str, Any]:
        """Check service health

        Returns:
            Health status dictionary
        """
        with self.traced_operation("health_check"):
            try:
                # Test HTTP client
                response = await self.client.get("https://httpbin.org/status/200")
                http_ok = response.status_code == 200

                # Check Playwright availability
                playwright_available = False
                try:
                    async with async_playwright() as p:
                        playwright_available = True
                except Exception:
                    pass

                return {
                    "service": "WebScrapingService",
                    "status": "healthy",
                    "http_client": "ok" if http_ok else "error",
                    "playwright_available": playwright_available,
                    "cache_size": len(self.cache),
                    "storage_type": self.settings.storage.type
                }
            except Exception as e:
                self.logger.error(f"Health check failed: {str(e)}")
                return {
                    "service": "WebScrapingService",
                    "status": "unhealthy",
                    "error": str(e)
                }

    async def scrape_webpage(
        self,
        url: str,
        use_javascript: bool = False,
        user_id: str = "anonymous",
        session_id: Optional[str] = None
    ) -> DocumentMessage:
        """Scrape a webpage and convert to markdown

        Args:
            url: URL to scrape
            use_javascript: Whether to use Playwright for JS rendering
            user_id: User identifier
            session_id: Session identifier

        Returns:
            DocumentMessage with scraped content
        """
        with self.traced_operation(
            "scrape_webpage",
            url=url,
            use_javascript=use_javascript,
            user_id=user_id,
            session_id=session_id
        ):
            try:
                # Check cache first
                cache_key = f"{url}:{use_javascript}"
                if cache_key in self.cache:
                    cached = self.cache[cache_key]
                    if datetime.utcnow() - cached['timestamp'] < self.cache_duration:
                        self.logger.info(f"Returning cached content for {url}")
                        return cached['document']

                # Create document message
                doc_id = hashlib.sha256(url.encode()).hexdigest()[:12]
                document = DocumentMessage(
                    metadata=DocumentMetadata(
                        document_id=doc_id,
                        document_type=DocumentType.WEBPAGE,
                        name="",  # Will be updated after scraping
                        created_user=user_id,
                        updated_user=user_id,
                        source_url=url,
                        tags=["webpage", "scraping"]
                    ),
                    content=DocumentContent(
                        raw_text="",
                        formatted_content=""
                    ),
                    user_id=user_id,
                    session_id=session_id
                )

                # Scrape content
                if use_javascript:
                    html_content, title = await self._scrape_with_playwright(url)
                else:
                    html_content, title = await self._scrape_with_httpx(url)

                # Convert to markdown
                markdown_content = await self._html_to_markdown(html_content, url)

                # Extract metadata from HTML
                soup = BeautifulSoup(html_content, 'html.parser')
                metadata = self._extract_metadata(soup)

                # Update document
                document.metadata.name = title or metadata.get('title', 'Untitled')
                document.content.raw_text = markdown_content
                document.content.formatted_content = markdown_content

                # Add metadata as structured data
                document.content.structured_data = {
                    "source": "web_scraping",
                    "url": url,
                    "scraped_at": datetime.utcnow().isoformat(),
                    "description": metadata.get('description'),
                    "keywords": metadata.get('keywords'),
                    "author": metadata.get('author')
                }

                # Update metadata
                document.metadata.updated_timestamp = datetime.utcnow()
                document.metadata.summary = markdown_content[:200] + "..." if len(markdown_content) > 200 else markdown_content

                # Store document
                await self.storage.store(doc_id, document.model_dump())

                # Update cache
                self.cache[cache_key] = {
                    'document': document,
                    'timestamp': datetime.utcnow()
                }

                self.logger.info(f"Successfully scraped webpage: {url}")
                return document

            except Exception as e:
                self.logger.error(f"Failed to scrape webpage {url}: {str(e)}")
                raise

    async def _scrape_with_httpx(self, url: str) -> tuple[str, str]:
        """Scrape webpage using httpx (for simple HTML)

        Args:
            url: URL to scrape

        Returns:
            Tuple of (HTML content, page title)
        """
        with self.traced_operation("scrape_with_httpx", url=url):
            try:
                response = await self.client.get(url)
                response.raise_for_status()

                html_content = response.text

                # Extract title
                soup = BeautifulSoup(html_content, 'html.parser')
                title_tag = soup.find('title')
                title = title_tag.get_text(strip=True) if title_tag else ""

                return html_content, title

            except Exception as e:
                self.logger.error(f"Failed to scrape with httpx: {str(e)}")
                raise

    async def _scrape_with_playwright(self, url: str) -> tuple[str, str]:
        """Scrape webpage using Playwright (for JS-heavy sites)

        Args:
            url: URL to scrape

        Returns:
            Tuple of (HTML content, page title)
        """
        with self.traced_operation("scrape_with_playwright", url=url):
            try:
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    try:
                        page = await browser.new_page()

                        # Set viewport and user agent
                        await page.set_viewport_size({"width": 1920, "height": 1080})

                        # Navigate to page
                        await page.goto(url, wait_until="networkidle")

                        # Wait for content to load (adaptive waiting)
                        try:
                            await page.wait_for_load_state("networkidle")
                        except Exception:
                            # Fallback to DOM content loaded
                            await page.wait_for_load_state("domcontentloaded")

                        # Get page content after JS execution
                        html_content = await page.content()

                        # Get title
                        title = await page.title()

                        return html_content, title

                    finally:
                        await browser.close()

            except Exception as e:
                self.logger.error(f"Failed to scrape with playwright: {str(e)}")
                # Fallback to httpx
                self.logger.info(f"Falling back to httpx for {url}")
                return await self._scrape_with_httpx(url)

    async def _html_to_markdown(self, html_content: str, base_url: str) -> str:
        """Convert HTML to markdown with proper formatting

        Args:
            html_content: HTML content
            base_url: Base URL for resolving relative links

        Returns:
            Markdown formatted content
        """
        with self.traced_operation("html_to_markdown"):
            try:
                # Parse HTML
                soup = BeautifulSoup(html_content, 'html.parser')

                # Remove script and style tags
                for script in soup(["script", "style"]):
                    script.decompose()

                # Convert relative URLs to absolute
                for tag in soup.find_all(['a', 'img']):
                    if tag.name == 'a' and tag.get('href'):
                        tag['href'] = urljoin(base_url, tag['href'])
                    elif tag.name == 'img' and tag.get('src'):
                        tag['src'] = urljoin(base_url, tag['src'])

                # Extract main content (try to find article or main tags)
                main_content = None
                for selector in ['main', 'article', '[role="main"]', '#content', '.content']:
                    main_content = soup.select_one(selector)
                    if main_content:
                        break

                # If no main content found, use body
                if not main_content:
                    main_content = soup.find('body') or soup

                # Convert to markdown
                markdown = self.html2text.handle(str(main_content))

                # Clean up markdown
                markdown = self._clean_markdown(markdown)

                return markdown

            except Exception as e:
                self.logger.error(f"Failed to convert HTML to markdown: {str(e)}")
                # Fallback to simple text extraction
                return soup.get_text(separator='\n', strip=True)

    def _clean_markdown(self, markdown: str) -> str:
        """Clean up markdown content

        Args:
            markdown: Raw markdown

        Returns:
            Cleaned markdown
        """
        # Remove excessive blank lines
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)

        # Fix broken markdown links
        markdown = re.sub(r'\[([^\]]+)\]\s+\(([^)]+)\)', r'[\1](\2)', markdown)

        # Remove HTML comments
        markdown = re.sub(r'<!--.*?-->', '', markdown, flags=re.DOTALL)

        # Trim whitespace
        markdown = markdown.strip()

        return markdown

    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract metadata from HTML

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            Metadata dictionary
        """
        metadata = {}

        # Title
        title_tag = soup.find('title')
        if title_tag:
            metadata['title'] = title_tag.get_text(strip=True)

        # Meta description
        desc_tag = soup.find('meta', attrs={'name': 'description'})
        if desc_tag and desc_tag.get('content'):
            metadata['description'] = desc_tag['content']

        # Meta keywords
        keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
        if keywords_tag and keywords_tag.get('content'):
            metadata['keywords'] = keywords_tag['content']

        # Author
        author_tag = soup.find('meta', attrs={'name': 'author'})
        if author_tag and author_tag.get('content'):
            metadata['author'] = author_tag['content']

        # Open Graph data
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            metadata['og_title'] = og_title['content']

        og_desc = soup.find('meta', property='og:description')
        if og_desc and og_desc.get('content'):
            metadata['og_description'] = og_desc['content']

        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            metadata['og_image'] = og_image['content']

        # Published date
        published = soup.find('meta', property='article:published_time')
        if published and published.get('content'):
            metadata['published_date'] = published['content']

        return metadata

    async def extract_links(self, url: str) -> List[str]:
        """Extract all links from a webpage

        Args:
            url: URL to extract links from

        Returns:
            List of absolute URLs
        """
        with self.traced_operation("extract_links", url=url):
            try:
                html_content, _ = await self._scrape_with_httpx(url)
                soup = BeautifulSoup(html_content, 'html.parser')

                links = []
                for tag in soup.find_all('a', href=True):
                    absolute_url = urljoin(url, tag['href'])
                    if absolute_url.startswith('http'):
                        links.append(absolute_url)

                # Remove duplicates while preserving order
                seen = set()
                unique_links = []
                for link in links:
                    if link not in seen:
                        seen.add(link)
                        unique_links.append(link)

                self.logger.info(f"Extracted {len(unique_links)} unique links from {url}")
                return unique_links

            except Exception as e:
                self.logger.error(f"Failed to extract links from {url}: {str(e)}")
                raise

    async def clear_cache(self) -> Dict[str, Any]:
        """Clear the scraping cache

        Returns:
            Cache statistics
        """
        with self.traced_operation("clear_cache"):
            size_before = len(self.cache)
            self.cache.clear()

            return {
                "entries_cleared": size_before,
                "cache_size": 0
            }

    async def cleanup(self):
        """Cleanup resources"""
        with self.traced_operation("cleanup"):
            try:
                # Close HTTP client
                await self.client.aclose()

                # Close browser if open
                if self.browser:
                    await self.browser.close()

                # Clear cache
                self.cache.clear()

                self.logger.info("WebScrapingService cleanup completed")

            except Exception as e:
                self.logger.error(f"Cleanup failed: {str(e)}")


# Register with factory
from .service_factory import ServiceFactory, ServiceType
ServiceFactory.register(ServiceType.WEB_SCRAPING, WebScrapingService)