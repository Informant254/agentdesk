"""MCP Server Registry - Central registry for all MCP servers."""

from backend.mcp_servers.google_calendar import google_calendar_server
from backend.mcp_servers.google_maps import google_maps_server
from backend.mcp_servers.jobber import jobber_server


MCP_SERVERS = {
    "google_calendar": google_calendar_server,
    "google_maps": google_maps_server,
    "jobber": jobber_server,
}


def get_mcp_server(name: str):
    """Get an MCP server by name."""
    server = MCP_SERVERS.get(name)
    if not server:
        raise ValueError(f"MCP server '{name}' not found. Available: {list(MCP_SERVERS.keys())}")
    return server


def list_mcp_servers() -> list[str]:
    """List all registered MCP server names."""
    return list(MCP_SERVERS.keys())
