# Web MCP Server - Dockerfile
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libgcc1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    lsb-release \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy pyproject.toml and uv.lock
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen --no-dev

# Install Playwright browsers
RUN /app/.venv/bin/playwright install chromium

# Copy the application code
COPY server.py ./
COPY generate_config.py ./

# Create non-root user for security
RUN useradd -m -u 1000 webmcp && \
    chown -R webmcp:webmcp /app

USER webmcp

# Expose port for remote mode
EXPOSE 8000

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/app/.ms-playwright

# Default command - run in local mode
CMD ["/app/.venv/bin/python", "server.py", "--mode", "local"]

# Alternative commands for remote mode:
# CMD ["/app/.venv/bin/python", "server.py", "--mode", "remote", "--host", "0.0.0.0", "--port", "8000"]
# With authentication:
# CMD ["/app/.venv/bin/python", "server.py", "--mode", "remote", "--host", "0.0.0.0", "--port", "8000", "--token", "your-secret-token"]
