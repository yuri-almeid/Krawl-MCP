"""
Unit tests for Web MCP Server

Tests cover:
- search_web functionality
- scrape_webpage functionality
- Error handling
- URL validation
- Token optimization
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add parent directory to path to import server module
sys.path.insert(0, str(Path(__file__).parent.parent))

from server import (
    extract_markdown,
    scrape_webpage,
    scrape_with_playwright,
    search_duckduckgo,
    search_web,
    validate_url,
)


class TestValidateUrl:
    """Tests for URL validation."""

    def test_valid_http_url(self):
        """Test valid HTTP URL."""
        assert validate_url("http://example.com") is True

    def test_valid_https_url(self):
        """Test valid HTTPS URL."""
        assert validate_url("https://example.com") is True

    def test_valid_https_with_path(self):
        """Test valid HTTPS URL with path."""
        assert validate_url("https://example.com/path/to/page") is True

    def test_valid_https_with_query(self):
        """Test valid HTTPS URL with query parameters."""
        assert validate_url("https://example.com?query=test") is True

    def test_invalid_no_scheme(self):
        """Test URL without scheme."""
        assert validate_url("example.com") is False

    def test_invalid_ftp_scheme(self):
        """Test FTP scheme (not allowed)."""
        assert validate_url("ftp://example.com") is False

    def test_invalid_empty_string(self):
        """Test empty string."""
        assert validate_url("") is False

    def test_invalid_none(self):
        """Test None value."""
        assert validate_url(None) is False

    def test_invalid_malformed(self):
        """Test malformed URL."""
        assert validate_url("not-a-url") is False


class TestExtractMarkdown:
    """Tests for Markdown extraction."""

    def test_extract_from_simple_html(self):
        """Test extraction from simple HTML."""
        html = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Main Heading</h1>
                <p>This is a paragraph with <strong>bold text</strong>.</p>
            </body>
        </html>
        """
        result = extract_markdown(html)
        assert "Main Heading" in result
        assert "bold text" in result

    def test_extract_from_html_with_links(self):
        """Test extraction preserves links."""
        html = """
        <html>
            <body>
                <p>Check out <a href="https://example.com">this link</a></p>
            </body>
        </html>
        """
        result = extract_markdown(html)
        assert "this link" in result

    def test_extract_from_html_with_tables(self):
        """Test extraction handles tables."""
        html = """
        <html>
            <body>
                <table>
                    <tr><th>Header</th></tr>
                    <tr><td>Cell 1</td></tr>
                </table>
            </body>
        </html>
        """
        result = extract_markdown(html)
        # Tables should be included (include_tables=True)
        assert len(result) > 0

    def test_extract_from_empty_html(self):
        """Test extraction from empty HTML."""
        html = ""
        result = extract_markdown(html)
        assert result == ""

    def test_extract_from_html_with_scripts(self):
        """Test extraction removes scripts."""
        html = """
        <html>
            <body>
                <h1>Content</h1>
                <script>alert('removed');</script>
                <p>Text after script</p>
            </body>
        </html>
        """
        result = extract_markdown(html)
        assert "Content" in result
        assert "Text after script" in result
        assert "alert" not in result


class TestSearchDuckDuckGo:
    """Tests for DuckDuckGo search functionality."""

    @pytest.mark.asyncio
    async def test_successful_search(self):
        """Test successful search returns results."""
        mock_results = [
            {
                "title": "Python Async Programming",
                "url": "https://example.com/python-async",
                "body": "Learn about Python's async/await syntax",
            },
            {
                "title": "Asyncio Best Practices",
                "url": "https://example.com/asyncio-guide",
                "body": "Guide to using asyncio effectively",
            },
        ]

        mock_ddgs = MagicMock()
        mock_ddgs.news.return_value = iter(mock_results)
        mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
        mock_ddgs.__exit__ = MagicMock(return_value=False)

        with patch("server.DDGS", return_value=mock_ddgs):
            results = await search_duckduckgo("python async")

        assert len(results) == 2
        assert results[0]["title"] == "Python Async Programming"
        assert results[0]["url"] == "https://example.com/python-async"
        assert results[0]["snippet"] == "Learn about Python's async/await syntax"

    @pytest.mark.asyncio
    async def test_search_with_empty_results(self):
        """Test search with no results."""
        mock_ddgs = MagicMock()
        mock_ddgs.news.return_value = iter([])
        mock_ddgs.__enter__ = MagicMock(return_value=mock_ddgs)
        mock_ddgs.__exit__ = MagicMock(return_value=False)

        with patch("server.DDGS", return_value=mock_ddgs):
            results = await search_duckduckgo("nonexistent query")

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_with_error(self):
        """Test search with error handling."""
        with patch("server.DDGS", side_effect=Exception("Search error")):
            with pytest.raises(RuntimeError, match="Search failed"):
                await search_duckduckgo("test query")


class TestScrapeWithPlaywright:
    """Tests for Playwright scraping functionality."""

    @pytest.mark.asyncio
    async def test_successful_scrape(self):
        """Test successful page scrape."""
        mock_html = "<html><body><h1>Test Content</h1></body></html>"

        mock_page = AsyncMock()
        mock_page.content = AsyncMock(return_value=mock_html)
        mock_page.goto = AsyncMock()
        mock_page.set_default_timeout = MagicMock()

        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)
        mock_browser.close = AsyncMock()

        mock_playwright = AsyncMock()
        mock_playwright.chromium = MagicMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_playwright.__aenter__ = AsyncMock(return_value=mock_playwright)
        mock_playwright.__aexit__ = AsyncMock()

        with patch("server.async_playwright", return_value=mock_playwright):
            result = await scrape_with_playwright("https://example.com")

        assert result == mock_html
        mock_browser.close.assert_called_once()


class TestSearchWeb:
    """Tests for search_web tool."""

    @pytest.mark.asyncio
    async def test_search_web_with_results(self):
        """Test search_web returns formatted results."""
        mock_results = [
            {
                "title": "Test Result 1",
                "url": "https://example.com/1",
                "snippet": "Snippet 1",
            }
        ]

        with patch(
            "server.search_duckduckgo",
            new_callable=AsyncMock,
            return_value=mock_results,
        ):
            result = await search_web("test query")

        assert "Test Result 1" in result
        assert "https://example.com/1" in result
        assert "Snippet 1" in result
        assert "Search Results for" in result

    @pytest.mark.asyncio
    async def test_search_web_empty_query(self):
        """Test search_web with empty query."""
        result = await search_web("")
        assert "Error: Search query cannot be empty" in result

    @pytest.mark.asyncio
    async def test_search_web_whitespace_query(self):
        """Test search_web with whitespace query."""
        result = await search_web("   ")
        assert "Error: Search query cannot be empty" in result

    @pytest.mark.asyncio
    async def test_search_web_no_results(self):
        """Test search_web with no results."""
        with patch("server.search_duckduckgo", new_callable=AsyncMock, return_value=[]):
            result = await search_web("nonexistent query")

        assert "No results found" in result
        assert "nonexistent query" in result

    @pytest.mark.asyncio
    async def test_search_web_with_error(self):
        """Test search_web with error."""
        with patch(
            "server.search_duckduckgo",
            new_callable=AsyncMock,
            side_effect=RuntimeError("API error"),
        ):
            result = await search_web("test query")

        assert "Search Error" in result
        assert "API error" in result

    @pytest.mark.asyncio
    async def test_search_web_max_five_results(self):
        """Test search_web handles up to 5 results (from MAX_SEARCH_RESULTS constant)."""
        mock_results = [
            {
                "title": f"Result {i}",
                "url": f"https://example.com/{i}",
                "snippet": f"Snippet {i}",
            }
            for i in range(1, 6)  # 5 results (matching MAX_SEARCH_RESULTS)
        ]

        with patch(
            "server.search_duckduckgo",
            new_callable=AsyncMock,
            return_value=mock_results,
        ):
            result = await search_web("test query")

        # Should show all 5 results
        assert "Result 1" in result
        assert "Result 5" in result


class TestScrapeWebpage:
    """Tests for scrape_webpage tool."""

    @pytest.mark.asyncio
    async def test_scrape_webpage_success(self):
        """Test scrape_webpage with valid URL."""
        mock_html = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Main Content</h1>
                <p>Paragraph with <strong>formatting</strong></p>
            </body>
        </html>
        """
        mock_markdown = "# Main Content\n\nParagraph with **formatting**\n"

        with patch(
            "server.scrape_with_playwright",
            new_callable=AsyncMock,
            return_value=mock_html,
        ):
            with patch(
                "server.asyncio.to_thread",
                new_callable=AsyncMock,
                return_value=mock_markdown,
            ):
                result = await scrape_webpage("https://example.com")

        assert "Main Content" in result
        assert "Content from:" in result

    @pytest.mark.asyncio
    async def test_scrape_webpage_empty_url(self):
        """Test scrape_webpage with empty URL."""
        result = await scrape_webpage("")
        assert "Error: URL cannot be empty" in result

    @pytest.mark.asyncio
    async def test_scrape_webpage_invalid_url(self):
        """Test scrape_webpage with invalid URL."""
        result = await scrape_webpage("not-a-url")
        assert "Error: Invalid URL format" in result

    @pytest.mark.asyncio
    async def test_scrape_webpage_invalid_scheme(self):
        """Test scrape_webpage with invalid scheme."""
        result = await scrape_webpage("ftp://example.com")
        assert "Error: Invalid URL format" in result

    @pytest.mark.asyncio
    async def test_scrape_webpage_no_content(self):
        """Test scrape_webpage when no content can be extracted."""
        mock_html = "<html><body></body></html>"

        with patch(
            "server.scrape_with_playwright",
            new_callable=AsyncMock,
            return_value=mock_html,
        ):
            with patch(
                "server.asyncio.to_thread", new_callable=AsyncMock, return_value=""
            ):
                result = await scrape_webpage("https://example.com")

        assert "Warning: No content could be extracted" in result
        assert "https://example.com" in result

    @pytest.mark.asyncio
    async def test_scrape_webpage_timeout_error(self):
        """Test scrape_webpage with timeout error."""
        with patch(
            "server.scrape_with_playwright",
            new_callable=AsyncMock,
            side_effect=Exception("Timeout"),
        ):
            result = await scrape_webpage("https://example.com")

        assert "Error:" in result
        assert "timeout" in result.lower()

    @pytest.mark.asyncio
    async def test_scrape_webpage_navigation_error(self):
        """Test scrape_webpage with navigation error."""
        with patch(
            "server.scrape_with_playwright",
            new_callable=AsyncMock,
            side_effect=Exception("Navigation failed"),
        ):
            result = await scrape_webpage("https://example.com")

        assert "Error:" in result
        assert "Failed to navigate" in result or "scraping" in result.lower()


class TestTokenOptimization:
    """Tests for token optimization features."""

    def test_extract_markdown_removes_scripts(self):
        """Test that scripts are removed from content."""
        html = """
        <html>
            <body>
                <h1>Real Content</h1>
                <script>
                    var x = 100;
                    console.log(x);
                </script>
                <p>More content</p>
                <script>alert('another script');</script>
            </body>
        </html>
        """
        result = extract_markdown(html)
        assert "var x = 100" not in result
        assert "alert" not in result
        assert "Real Content" in result
        assert "More content" in result

    def test_extract_markdown_reduces_whitespace(self):
        """Test that excessive whitespace is reduced."""
        html = """
        <html>
            <body>
                <h1>Heading</h1>
                <p>Para 1</p>
                <p>Para 2</p>
            </body>
        </html>
        """
        result = extract_markdown(html)
        # Should not have excessive empty lines
        assert result.count("\n\n") < 10


class TestIntegration:
    """Integration tests for the server."""

    @pytest.mark.asyncio
    async def test_search_and_scrape_workflow(self):
        """Test a realistic workflow: search then scrape a result."""
        # Mock search results
        mock_results = [
            {
                "title": "Python Documentation",
                "url": "https://docs.python.org",
                "snippet": "Official Python documentation",
            }
        ]

        # Mock scrape result
        mock_html = "<html><body><h1>Python Docs</h1></body></html>"
        mock_markdown = "# Python Docs\n"

        with patch(
            "server.search_duckduckgo",
            new_callable=AsyncMock,
            return_value=mock_results,
        ):
            search_result = await search_web("python documentation")

        assert "Python Documentation" in search_result
        assert "https://docs.python.org" in search_result

        with patch(
            "server.scrape_with_playwright",
            new_callable=AsyncMock,
            return_value=mock_html,
        ):
            with patch(
                "server.asyncio.to_thread",
                new_callable=AsyncMock,
                return_value=mock_markdown,
            ):
                scrape_result = await scrape_webpage("https://docs.python.org")

        assert "Python Docs" in scrape_result
