"""
MCP Server for Graph Analytics AI

Exposes the graph analytics platform as an MCP server so that any
MCP-compatible AI host (Claude Desktop, Cursor, etc.) can invoke
graph analytics workflows as tools.

Usage:
    python -m graph_analytics_ai.mcp

Or via the installed console script:
    gaai-mcp
"""

from .server import mcp, create_server

__all__ = ["mcp", "create_server"]
