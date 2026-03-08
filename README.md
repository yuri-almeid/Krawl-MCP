# Krawl MCP Server

A self-hosted MCP server providing Web Search and Web Scraping capabilities using only free, open-source tools. Supports both local (stdio) and remote (Streamable HTTP) execution modes with optional authentication.

## Features

- **Web Search**: Search using DuckDuckGo (no API key required)
- **Web Scraping**: Scrape webpages with JavaScript rendering support
- **Dual Mode**: Local (stdio) or Remote (Streamable HTTP) execution
- **Authentication**: Optional Bearer token authentication for remote mode
- **Self-hosted**: No paid external APIs
- **Token Optimized**: Returns clean Markdown content, not raw HTML
- **Async/Await**: Non-blocking operations for responsive MCP server

## Tech Stack

- **fastmcp**: High-level MCP server framework
- **duckduckgo-search**: Free web search via DDGS
- **playwright**: Headless browser with JavaScript support
- **trafilatura**: Content extraction and Markdown conversion
- **uv**: Fast Python package manager
- **Streamable HTTP**: Modern bidirectional transport for remote communication

## Project Setup

### Prerequisites

- Python 3.12+
- uv package manager

### Configuration (.env file)

Create a `.env` file in the project root for configuration:

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your settings
```

**`.env` file options:**

| Variable | Description | Default |
|----------|-------------|---------|
| `MODE` | Server mode: `local` or `remote` | `local` |
| `PORT` | Port for remote mode | `8000` |
| `MCP_AUTH_TOKEN` | Authentication token for remote mode (leave empty to disable) | (empty) |
| `LOG_LEVEL` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` |
| `MAX_SEARCH_RESULTS` | Maximum number of search results to return | `5` |
| `SCRAPER_TIMEOUT` | Scraper timeout in milliseconds (30s default) | `30000` |
| `BROWSER_TIMEOUT` | Browser timeout in milliseconds (60s default) | `60000` |
| `USER_AGENT` | User agent string for web requests | Standard desktop browser |

The `.env` file is automatically loaded when running the server. Command-line arguments override `.env` values.

### Installation

```bash
# 1. Navigate to project directory
cd krawl-mcp

# 2. Create virtual environment
uv venv

# 3. Install dependencies
uv add fastmcp duckduckgo-search playwright trafilatura

# 4. Install Playwright browsers (Chromium)
uv run playwright install chromium
```

## Running the Server

### Local Mode (stdio)

The default mode for local development:

```bash
# Activate virtual environment (optional)
source .venv/bin/activate

# Run in local mode (reads from .env if exists)
python server.py

# Or explicitly specify mode
python server.py --mode local
```

### Remote Mode (Streamable HTTP)

Run as an HTTP server accessible over the network:

```bash
# Run in remote mode (reads MODE=remote from .env)
python server.py

# Or specify mode explicitly
python server.py --mode remote

# Custom port (overrides PORT in .env)
python server.py --mode remote --port 9000

# Authentication token via .env (recommended)
# Set MCP_AUTH_TOKEN in .env file, then:
python server.py --mode remote

# Or override via command line
python server.py --mode remote --token "your-secret-token"

# With verbose logging (overrides LOG_LEVEL in .env)
python server.py --mode remote --log-level DEBUG
```

### Authentication (Remote Mode)

To enable authentication for remote mode, set the token in your `.env` file:

```bash
# In .env file:
MCP_AUTH_TOKEN=your-secret-token-here
```

Then run:
```bash
python server.py --mode remote
```

**Alternative methods:**

```bash
# Option 1: Environment variable
export MCP_AUTH_TOKEN="your-secret-token"
python server.py --mode remote

# Option 2: Command line argument (overrides .env and env var)
python server.py --mode remote --token "your-secret-token"

# Generate a random token (example)
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Priority:** Command-line argument > Environment variable > `.env` file

**⚠️ Security Warning**: Running in remote mode without authentication allows anyone to access your server!

### Health Check Endpoint

Remote mode includes a health check endpoint:

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "mode": "remote",
  "auth_enabled": true,
  "tools": ["search_web", "scrape_webpage"]
}
```

## MCP Client Configuration

**Note for Remote Mode:** Before connecting, make sure the server is running in remote mode:

```bash
uv run python server.py --mode remote
```

### Local Mode Configuration (stdio)

Add to your MCP client configuration:

```json
{
  "mcpServers": {
    "krawl-mcp": {
      "command": "/Users/yuri/.local/share/uv/python/cpython-3.12.9-macos-aarch64-none/bin/python",
      "args": ["/Users/yuri/dev/personal/krawl_mcp/server.py", "--mode", "local"],
      "env": {}
    }
  }
}
```

**Important**: Replace the paths with your actual project paths. Use `python generate_config.py` to get the correct paths.

### Remote Mode with mcp-remote (Recommended)

If you have `mcp-remote` installed, you can connect to the remote Streamable HTTP server:

```json
{
  "mcpServers": {
    "krawl-mcp": {
      "command": "/opt/homebrew/bin/npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://localhost:8000/mcp",
        "--header",
        "Authorization:Bearer YOUR_TOKEN",
        "--name",
        "krawl-mcp"
      ],
      "env": {
        "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
      }
    }
  }
}
```

**Important**: Replace `YOUR_TOKEN` with your actual authentication token. The server must be running first:

```bash
uv run python server.py --mode remote
```

### Remote Mode Configuration (No Authentication)

```json
{
  "mcpServers": {
    "krawl-mcp": {
      "url": "http://your-server:8000/mcp",
      "transport": "streamable-http",
      "env": {}
    }
  }
}
```

### Remote Mode Configuration (With Authentication)

```json
{
  "mcpServers": {
    "krawl-mcp": {
      "url": "http://your-server:8000/mcp",
      "transport": "streamable-http",
      "headers": {
        "Authorization": "Bearer your-secret-token"
      },
      "env": {}
    }
  }
}
```

Replace `your-secret-token` with your actual authentication token.

### Configuration for Claude Desktop

**Local mode (macOS):**
```json
{
  "mcpServers": {
    "krawl-mcp": {
      "command": "/Users/yourname/.local/share/uv/python/cpython-3.12.9-macos-aarch64-none/bin/python",
      "args": ["/Users/yourname/dev/personal/krawl_mcp/server.py", "--mode", "local"]
    }
  }
}
```

**Remote mode with mcp-remote (recommended):**
```json
{
  "mcpServers": {
    "krawl-mcp": {
      "command": "/opt/homebrew/bin/npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://localhost:8000/mcp",
        "--header",
        "Authorization:Bearer YOUR_TOKEN",
        "--name",
        "krawl-mcp"
      ],
      "env": {
        "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
      }
    }
  }
}
```

**Remote server (non-localhost) with mcp-remote:**

When connecting to a remote server (not localhost), you must add the `--allow-http` flag since Claude Desktop requires HTTPS for non-localhost URLs:

```json
{
  "mcpServers": {
    "krawl-mcp": {
      "command": "/opt/homebrew/bin/npx",
      "args": [
        "mcp-remote",
        "http://100.86.193.50:6656/mcp",
        "--name",
        "krawl-mcp",
        "--header",
        "Authorization: Bearer ${AUTH_TOKEN}",
        "--allow-http"
      ],
      "env": {
        "AUTH_TOKEN": "your-secret-token-here",
        "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
      }
    }
  }
}
```

**Important notes:**
- Replace `http://100.86.193.50:6656/mcp` with your server URL
- Replace `your-secret-token-here` with your actual `MCP_AUTH_TOKEN`
- The `--allow-http` flag is required for non-localhost HTTP URLs
- For production, use HTTPS and remove the `--allow-http` flag

**Direct Streamable HTTP mode (with authentication):**
```json
{
  "mcpServers": {
    "krawl-mcp": {
      "url": "http://localhost:8000/mcp",
      "transport": "streamable-http",
      "headers": {
        "Authorization": "Bearer your-secret-token"
      }
    }
  }
}
```

## Available Tools

### `search_web`

Search the web using DuckDuckGo.

**Input:**
- `query` (string): Search query

**Output:** Top results with Title, URL, and Snippet (default: 5 results, configurable via `MAX_SEARCH_RESULTS`)

**Example:**
```python
await call_tool("search_web", {"query": "Python async programming"})
```

### `scrape_webpage`

Scrape a webpage and return clean Markdown content.

**Input:**
- `url` (string): URL to scrape

**Output:** Clean textual content in Markdown format

**Example:**
```python
await call_tool("scrape_webpage", {"url": "https://example.com"})
```

## Architecture

### Transport Modes

The server supports two transport modes:

#### Local Mode (stdio)
- Communication via standard input/output
- Best for local development
- Lower latency
- No network setup required

#### Remote Mode (Streamable HTTP)
- Communication via modern bidirectional HTTP transport
- Allows remote access to the server
- Supports multiple clients
- Requires network configuration
- Optional authentication

### Authentication

Simple Bearer token authentication:
- Validates token on each request
- Skips authentication for `/health` endpoint
- Case-sensitive token comparison
- Set via `--token` argument or `MCP_AUTH_TOKEN` environment variable

### Async/Await Pattern

The entire server is built using `asyncio` to ensure the MCP server remains responsive during I/O operations:

```python
# Native async library - direct usage
async with async_playwright() as p:
    await p.chromium.launch()

# Synchronous library - wrapped in thread pool
results = await asyncio.to_thread(synchronous_function)
```

### Synchronous Library Integration

- **DDGS (DuckDuckGo)**: Wrapped with `asyncio.to_thread()` since it's synchronous
- **Trafilatura**: Wrapped with `asyncio.to_thread()` since it's synchronous
- **Playwright**: Used in async mode natively (`async_playwright`)

### Token Optimization

The scraper returns only useful content:
- Trafilatura automatically removes menus, ads, scripts, and navigation
- Output is clean Markdown, not raw HTML
- Excessive whitespace is reduced

### Error Handling

- URL validation before processing
- Graceful timeout handling (30s default)
- Clear error messages for LLM consumption
- Browser cleanup guaranteed with try/finally

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=server --cov-report=html

# Run specific test files
uv run pytest test_server.py -v
uv run pytest test_auth_and_remote.py -v

# Run specific test class
uv run pytest test_server.py::TestValidateUrl -v

# Run specific test
uv run pytest test_server.py::TestValidateUrl::test_valid_http_url -v
```

### Test Coverage

The project includes comprehensive unit tests:

- **34 tests** in `test_server.py` - Core functionality
- **18 tests** in `test_auth_and_remote.py` - Authentication and remote mode

**Total: 52 tests with ~93% code coverage**

### Debugging

The server includes logging at INFO level by default:

```python
import logging
logging.basicConfig(level=logging.DEBUG)  # Add at top of server.py
```

Or use command line:
```bash
python server.py --log-level DEBUG
```

## Production Deployment

### Running as a System Service (Linux)

Create a systemd service file `/etc/systemd/system/krawl-mcp.service`:

```ini
[Unit]
Description=Krawl MCP Server
After=network.target

[Service]
Type=simple
User=krawl-mcp
WorkingDirectory=/path/to/krawl-mcp
Environment="MCP_AUTH_TOKEN=your-secret-token"
ExecStart=/path/to/krawl-mcp/.venv/bin/python server.py --mode remote --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable krawl-mcp
sudo systemctl start krawl-mcp
sudo systemctl status krawl-mcp
```

### Running with Docker Compose

The recommended way to deploy using Docker Compose:

**1. Create a `.env` file** (optional, for configuration):

```bash
# .env
MCP_AUTH_TOKEN=your-secret-token-here
PORT=8000
```

**2. Choose your mode** (edit `docker-compose.yml`):

For **local mode** (stdio, default):
```yaml
command: ["/app/.venv/bin/python", "server.py", "--mode", "local", "--log-level", "INFO"]
```

For **remote mode** (HTTP):
```yaml
command: ["/app/.venv/bin/python", "server.py", "--mode", "remote", "--host", "0.0.0.0", "--port", "8000", "--log-level", "INFO"]
```

For **remote mode with authentication**:
```yaml
command: ["/app/.venv/bin/python", "server.py", "--mode", "remote", "--host", "0.0.0.0", "--port", "8000", "--token", "${MCP_AUTH_TOKEN}", "--log-level", "INFO"]
```

**3. Start the service:**

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f krawl-mcp

# Stop the service
docker-compose down

# Rebuild after changes
docker-compose up -d --build
```

**4. Check health status:**

```bash
# Health endpoint (remote mode)
curl http://localhost:8000/health

# Container status
docker-compose ps
```

**Configuration Options:**

| Option | Environment Variable | Default |
|--------|---------------------|---------|
| Port | `PORT` | 8000 |
| Auth Token | `MCP_AUTH_TOKEN` | (none) |
| Mode | (command line) | local |

**Volume Mounts for Development:**

Uncomment in `docker-compose.yml` to enable live code reloading:
```yaml
volumes:
  - ./server.py:/app/server.py:ro
```

**Resource Limits (adjust in docker-compose.yml):**

- CPU: 0.5 - 2 cores
- Memory: 512MB - 2GB

### Running with Docker (without Compose)

Build and run directly with Docker:

```bash
# Build image
docker build -t krawl-mcp .

# Run in local mode
docker run --name krawl-mcp krawl-mcp

# Run in remote mode
docker run -p 8000:8000 --name krawl-mcp krawl-mcp \
  /app/.venv/bin/python server.py --mode remote --host 0.0.0.0 --port 8000

# Run with authentication
docker run -p 8000:8000 -e MCP_AUTH_TOKEN=your-token --name krawl-mcp krawl-mcp \
  /app/.venv/bin/python server.py --mode remote --host 0.0.0.0 --port 8000 --token your-token
```

## Limitations

- Some websites may block automated scraping
- Pages requiring login/authentication won't work
- Very large pages may hit timeout limits
- Rate limiting is not implemented (be respectful)
- Remote mode without authentication is insecure

## Security Considerations

- Always use authentication in production for remote mode
- Use strong, randomly generated tokens
- Use HTTPS in production (requires reverse proxy)
- Consider rate limiting for production deployments
- Monitor server logs for unauthorized access attempts
- Keep dependencies updated

## Command Line Options

```
usage: server.py [-h] [--mode {local,remote}] [--host HOST] [--port PORT]
                 [--token TOKEN] [--log-level {DEBUG,INFO,WARNING,ERROR}]

Krawl MCP Server - Web Search and Scraping

options:
  -h, --help            show this help message and exit
  --mode {local,remote}  Server mode: local (stdio) or remote (Streamable HTTP)
  --host HOST            Host address for remote mode (default: 0.0.0.0)
  --port PORT            Port for remote mode (default: 8000)
  --token TOKEN          Authentication token for remote mode (can also use MCP_AUTH_TOKEN env var)
  --log-level {DEBUG,INFO,WARNING,ERROR}
                        Logging level
```

## License

MIT
