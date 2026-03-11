"""
MCP Server entry point.

Creates the FastMCP server instance and registers all tool groups.
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "graph-analytics-ai",
    dependencies=["python-arango", "python-dotenv", "requests"],
)

# Register tool groups (imports trigger @mcp.tool() decorators)
from .tools import graph, workflow, catalog, gae  # noqa: F401, E402


def create_server() -> FastMCP:
    """Return the configured MCP server instance."""
    return mcp


def main() -> None:
    """Entry point for gaai-mcp console script."""
    mcp.run()


if __name__ == "__main__":
    main()
