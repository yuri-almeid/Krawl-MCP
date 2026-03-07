#!/usr/bin/env python3
"""
Helper script to generate MCP configuration with correct absolute paths.
Supports both local and remote modes.

Run this script to get the exact configuration for your system.
"""

import sys
from pathlib import Path
import argparse


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.resolve()


def get_python_path() -> Path:
    """Get the Python executable path in the venv."""
    return get_project_root() / ".venv" / "bin" / "python"


def get_server_path() -> Path:
    """Get the server.py path."""
    return get_project_root() / "server.py"


def generate_local_config() -> dict:
    """Generate local mode configuration."""
    python_path = get_python_path()
    server_path = get_server_path()

    # Verify paths exist
    if not python_path.exists():
        print(f"Error: Python not found at {python_path}")
        print("Please run: uv venv")
        sys.exit(1)

    if not server_path.exists():
        print(f"Error: server.py not found at {server_path}")
        sys.exit(1)

    return {
        "mcpServers": {
            "krawl-mcp": {
                "command": str(python_path),
                "args": [str(server_path), "--mode", "local"],
                "env": {}
            }
        }
    }


def generate_remote_config(host: str = "localhost", port: int = 8000, token: str = None) -> dict:
    """Generate remote mode configuration."""
    config = {
        "mcpServers": {
            "krawl-mcp": {
                "url": f"http://{host}:{port}/sse",
                "transport": "sse",
                "env": {}
            }
        }
    }

    if token:
        config["mcpServers"]["krawl-mcp"]["headers"] = {
            "Authorization": f"Bearer {token}"
        }

    return config


def main():
    """Generate and print the MCP configuration."""
    parser = argparse.ArgumentParser(description="Generate MCP configuration for Krawl MCP Server")
    parser.add_argument(
        "--mode",
        choices=["local", "remote"],
        default="local",
        help="Configuration mode: local or remote"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Remote server host (for remote mode)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Remote server port (for remote mode)"
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Authentication token (for remote mode)"
    )

    args = parser.parse_args()

    import json

    if args.mode == "local":
        config = generate_local_config()
        print(json.dumps(config, indent=2))
        print("\n" + "=" * 70)
        print("LOCAL MODE CONFIGURATION")
        print("=" * 70)
        print("\nCopy the above JSON to your MCP client configuration file:")
        print("  - Claude Desktop: ~/Library/Application Support/Claude/claude_desktop_config.json")
        print("  - Continue.dev: ~/.continue/config.json")
        print("=" * 70)
    else:
        config = generate_remote_config(args.host, args.port, args.token)
        print(json.dumps(config, indent=2))
        print("\n" + "=" * 70)
        print(f"REMOTE MODE CONFIGURATION (http://{args.host}:{args.port}/sse)")
        print("=" * 70)
        if args.token:
            print(f"✓ Authentication enabled with token: {args.token[:10]}...")
        else:
            print("⚠ WARNING: No authentication token configured!")
            print("  This is not secure for production use!")
        print("\nCopy the above JSON to your MCP client configuration file:")
        print("  - Claude Desktop: ~/Library/Application Support/Claude/claude_desktop_config.json")
        print("  - Continue.dev: ~/.continue/config.json")
        print("=" * 70)


if __name__ == "__main__":
    main()
