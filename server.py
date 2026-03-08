"""
Krawl MCP Server - Web Search and Web Scraping capabilities

This server provides two tools:
1. search_web - Search using DuckDuckGo
2. scrape_webpage - Scrape webpage content using Playwright + Trafilatura

Modes:
- Local (stdio): Default mode for local execution
- Remote (Streamable HTTP): HTTP-based mode with optional token authentication

Architecture Notes:
- All tools are async to prevent blocking the MCP server
- Synchronous libraries (DDGS, trafilatura) are wrapped with asyncio.to_thread
- Playwright has native async support (async_playwright)
- Error handling is comprehensive to provide clear feedback to the LLM
- Token optimization: scraper returns clean Markdown only, not raw HTML
- Authentication: Simple Bearer token for remote mode (optional)
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

# Load .env file if it exists
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

import trafilatura
from duckduckgo_search import DDGS
from fastmcp import FastMCP
from playwright.async_api import Page, async_playwright

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_config() -> Dict[str, Any]:
    """
    Centralized configuration retrieval.

    Returns a dictionary with all configuration values from environment variables
    with sensible defaults. This provides a single source of truth for configuration.

    Returns:
        Dict containing auth_token, auth_enabled, max_search_results,
        scraper_timeout, browser_timeout, and user_agent
    """
    return {
        "auth_token": os.getenv("MCP_AUTH_TOKEN", ""),
        "auth_enabled": bool(os.getenv("MCP_AUTH_TOKEN", "")),
        "max_search_results": int(os.getenv("MAX_SEARCH_RESULTS", "5")),
        "scraper_timeout": int(os.getenv("SCRAPER_TIMEOUT", "30000")),
        "browser_timeout": int(os.getenv("BROWSER_TIMEOUT", "60000")),
        "user_agent": os.getenv(
            "USER_AGENT",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        ),
    }


# Get configuration at module level for backward compatibility
_config = get_config()
MAX_SEARCH_RESULTS = _config["max_search_results"]
SCRAPER_TIMEOUT = _config["scraper_timeout"]
BROWSER_TIMEOUT = _config["browser_timeout"]
AUTH_TOKEN = _config["auth_token"]
AUTH_ENABLED = _config["auth_enabled"]
USER_AGENT = _config["user_agent"]


def validate_auth_token(token: Optional[str]) -> bool:
    """
    Validate authentication token for remote mode.

    Args:
        token: The Bearer token to validate

    Returns:
        True if token is valid or auth is disabled, False otherwise
    """
    # Read directly from environment to ensure test isolation
    auth_token = os.getenv("MCP_AUTH_TOKEN", "")
    auth_enabled = bool(auth_token)

    if not auth_enabled:
        return True
    if not token:
        return False
    # Simple token comparison (in production, use proper token validation)
    return token == auth_token


# Initialize FastMCP server with authentication support
mcp = FastMCP(
    "krawl-mcp",
    lifespan=None,
    # Add authentication middleware for remote mode
)


def validate_url(url: str) -> bool:
    """
    Basic URL validation to prevent injection attempts.
    Returns True if URL appears valid, False otherwise.
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and result.scheme in (
            "http",
            "https",
        )
    except Exception:
        return False


async def search_duckduckgo(query: str) -> List[Dict[str, str]]:
    """
    Perform search using DuckDuckGo (DDGS class).
    Wrapped in asyncio.to_thread because DDGS is synchronous.
    """

    def _search():
        results = []
        try:
            with DDGS() as ddgs:
                # Use 'news' endpoint for better structured results
                search_gen = ddgs.news(
                    keywords=query,
                    max_results=MAX_SEARCH_RESULTS,
                    timelimit="7d",  # Last 7 days for relevance
                )
                for result in search_gen:
                    results.append(
                        {
                            "title": result.get("title", "").strip(),
                            "url": result.get("url", "").strip(),
                            "snippet": result.get("body", "").strip(),
                        }
                    )
        except Exception as e:
            logger.error(f"DDGS search error: {e}")
            raise RuntimeError(f"Search failed: {str(e)}")
        return results

    # Run synchronous search in a thread pool
    return await asyncio.to_thread(_search)


async def scrape_with_playwright(url: str) -> str:
    """
    Scrape webpage using Playwright (headless browser).
    Returns HTML content for processing.
    """
    async with async_playwright() as p:
        # Launch browser in headless mode
        browser = await p.chromium.launch(headless=True)
        try:
            # Create new page with viewport
            page: Page = await browser.new_page(
                viewport={"width": 1280, "height": 800}, user_agent=USER_AGENT
            )

            # Set timeout for page operations
            page.set_default_timeout(SCRAPER_TIMEOUT)

            # Navigate to URL and wait for network to settle
            logger.info(f"Navigating to: {url}")
            await page.goto(
                url,
                wait_until="domcontentloaded",  # Wait for DOM to be ready
                timeout=BROWSER_TIMEOUT,
            )

            # Wait a bit more for any delayed JS rendering
            await asyncio.sleep(1)

            # Extract HTML
            html = await page.content()
            logger.info(f"Extracted HTML length: {len(html)}")

            return html

        finally:
            # Ensure browser is always closed
            await browser.close()


def extract_markdown(html: str) -> str:
    """
    Extract clean Markdown content from HTML using Trafilatura.
    Wrapped in asyncio.to_thread because trafilatura is synchronous.

    Trafilatura automatically:
    - Removes menus, ads, scripts, and navigation elements
    - Extracts main body text
    - Converts to clean Markdown format
    """
    # Use trafilatura's extract function with markdown output
    result = trafilatura.extract(
        html,
        output_format="markdown",  # Return clean Markdown
        include_comments=False,  # Exclude comments
        include_tables=True,  # Include tables in output
        include_formatting=True,  # Preserve text formatting
        url=None,  # We don't need URL for relative links resolution
        no_fallback=False,  # Use fallback extraction if needed
    )

    return result if result else ""


@mcp.tool()
async def search_web(query: str) -> str:
    """
    Search the web using DuckDuckGo.

    Args:
        query: The search query string

    Returns:
        A formatted string with top 5 search results, each containing:
        - Title
        - URL
        - Snippet
    """
    logger.info(
        f"Search request - Query: {query[:50]}{'...' if len(query) > 50 else ''}"
    )

    if not query or not query.strip():
        return "Error: Search query cannot be empty"

    try:
        results = await search_duckduckgo(query)

        if not results:
            logger.info(f"Search completed - No results found for: '{query}'")
            return f"No results found for query: '{query}'"

        # Format results for clean LLM consumption
        formatted = []
        formatted.append(f"## Search Results for: '{query}'")
        formatted.append("")

        for i, result in enumerate(results, 1):
            formatted.append(f"### {i}. {result['title']}")
            formatted.append(f"**URL:** {result['url']}")
            formatted.append(f"**Snippet:** {result['snippet']}")
            formatted.append("")

        result = "\n".join(formatted)
        logger.info(f"Search completed - Found {len(results)} results")
        return result

    except RuntimeError as e:
        return f"Search Error: {str(e)}"
    except Exception as e:
        logger.exception(f"Unexpected error in search_web: {e}")
        return f"Unexpected error during search: {str(e)}"


@mcp.tool()
async def scrape_webpage(url: str) -> str:
    """
    Scrape a webpage and return clean Markdown content.

    Uses Playwright to render the page (including JavaScript),
    then uses Trafilatura to extract and clean the main content.

    Args:
        url: The URL to scrape

    Returns:
        Clean textual content in Markdown format
    """
    logger.info(f"Scrape request - URL: {url}")

    # Validate URL first
    if not url or not url.strip():
        return "Error: URL cannot be empty"

    if not validate_url(url):
        logger.warning(f"Scrape failed - Invalid URL: {url}")
        return (
            f"Error: Invalid URL format. URLs must start with http:// or https:// "
            f"and include a domain (e.g., https://example.com). Received: '{url}'"
        )

    try:
        # Scrape HTML using Playwright
        html = await scrape_with_playwright(url)

        # Extract Markdown using Trafilatura (wrapped for async)
        markdown = await asyncio.to_thread(extract_markdown, html)

        if not markdown:
            logger.warning(f"Scrape failed - No content extracted from: {url}")
            return (
                f"Warning: No content could be extracted from '{url}'. "
                "The page might be empty, require JavaScript authentication, "
                "use content protection mechanisms, or block automated access."
            )

        # Token optimization: Remove excessive whitespace
        lines = markdown.split("\n")
        cleaned_lines = []
        prev_empty = False
        for line in lines:
            if line.strip() == "":
                if not prev_empty:
                    cleaned_lines.append("")
                prev_empty = True
            else:
                cleaned_lines.append(line)
                prev_empty = False

        cleaned_markdown = "\n".join(cleaned_lines)

        # Add metadata header for LLM context
        result = f"## Content from: {url}\n\n{cleaned_markdown}"
        logger.info(f"Scrape completed - Content length: {len(result)} chars")
        return result

    except Exception as e:
        logger.exception(f"Error in scrape_webpage for {url}: {e}")
        error_msg = str(e).lower()

        if "timeout" in error_msg:
            logger.warning(f"Scrape failed - Timeout for: {url}")
            return (
                f"Error: Page load timeout for '{url}'. The page may be too slow, "
                f"blocked, or require additional time. Try increasing SCRAPER_TIMEOUT "
                f"(current: {SCRAPER_TIMEOUT}ms)."
            )
        elif "navigation" in error_msg or "net::" in error_msg:
            logger.warning(f"Scrape failed - Navigation error for: {url}")
            return f"Error: Failed to navigate to '{url}'. The URL may be invalid, blocked, or the site is down."
        else:
            logger.warning(f"Scrape failed - Unexpected error for: {url}")
            return f"Error scraping '{url}': {str(e)}"


def check_connection() -> Dict[str, Any]:
    """
    Health check endpoint for remote mode.

    Returns:
        Dict with server status and configuration info
    """
    auth_enabled = bool(os.getenv("MCP_AUTH_TOKEN", ""))
    return {
        "status": "healthy",
        "mode": "remote",
        "auth_enabled": auth_enabled,
        "tools": ["search_web", "scrape_webpage"],
    }


def create_remote_app(auth_enabled: bool = False):
    """
    Create Streamable HTTP app for remote mode.

    Args:
        auth_enabled: Whether to enable Bearer token authentication

    Returns:
        Starlette app configured for Streamable HTTP transport with optional auth middleware
    """
    from starlette.middleware import Middleware
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse

    class AuthMiddleware(BaseHTTPMiddleware):
        """Simple Bearer token authentication middleware."""

        async def dispatch(self, request, call_next):
            # Skip auth for health check endpoint
            if request.url.path == "/health":
                return await call_next(request)

            # Check Authorization header
            auth_header = request.headers.get("Authorization", "")
            token = (
                auth_header.replace("Bearer ", "")
                if auth_header.startswith("Bearer ")
                else ""
            )

            if not validate_auth_token(token):
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "Unauthorized",
                        "message": "Invalid or missing authentication token",
                    },
                )

            return await call_next(request)

    async def health_check(request):
        return JSONResponse(check_connection())

    # Create app with optional middleware
    middleware = [Middleware(AuthMiddleware)] if auth_enabled else []
    app = mcp.http_app(transport="streamable-http", middleware=middleware)
    # Add health check route
    app.add_route("/health", health_check)
    return app


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Krawl MCP Server - Web Search and Scraping"
    )
    parser.add_argument(
        "--mode",
        choices=["local", "remote"],
        default=os.getenv("MODE", "local"),
        help="Server mode: local (stdio) or remote (Streamable HTTP) (default: from .env or 'local')",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host address for remote mode (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8000")),
        help="Port for remote mode (default: from .env or 8000)",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Authentication token for remote mode (overrides MCP_AUTH_TOKEN env var)",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=os.getenv("LOG_LEVEL", "INFO"),
        help="Logging level (default: from .env or INFO)",
    )

    args = parser.parse_args()

    # Set log level
    log_level = getattr(logging, args.log_level)
    logging.getLogger().setLevel(log_level)

    # Set token from argument if provided
    if args.token:
        os.environ["MCP_AUTH_TOKEN"] = args.token

    auth_enabled = bool(os.getenv("MCP_AUTH_TOKEN", ""))

    logger.info(f"Starting Krawl MCP Server in {args.mode} mode")

    if args.mode == "local":
        logger.info("Running in local mode (stdio transport)")
        mcp.run()

    else:  # remote mode
        logger.info(
            f"Running in remote mode (Streamable HTTP transport on {args.host}:{args.port})"
        )
        if auth_enabled:
            logger.info(
                "Authentication enabled (use token in MCP client or Authorization header)"
            )
        else:
            logger.warning(
                "WARNING: Running without authentication - anyone can access this server!"
            )

        # Create remote app with optional authentication
        app = create_remote_app(auth_enabled=auth_enabled)

        # Run the app
        import uvicorn

        uvicorn.run(app, host=args.host, port=args.port)
