"""
MCP (Model Context Protocol) integration using langchain-mcp-adapters
"""
import asyncio
from typing import Dict, Any, List, Optional
from langchain_core.tools import Tool
import logging

from src.core.config import settings

logger = logging.getLogger(__name__)

# Optional import of langchain-mcp-adapters; tolerate absence gracefully
try:
    from langchain_mcp_adapters.client import MultiServerMCPClient  # type: ignore
    MCP_ADAPTERS_AVAILABLE = True
except Exception as import_error:  # broad to catch transitive import errors
    MCP_ADAPTERS_AVAILABLE = False
    logger.warning(
        "MCP integration disabled: failed to import langchain-mcp-adapters (%s). The server will run without MCP tools.",
        import_error,
    )


class MCPToolManager:
    """Manager for MCP tools integration"""
    
    def __init__(self):
        # Use loose typing to avoid referencing missing symbols at runtime
        self.client: Optional[Any] = None
        self._initialized = False
        self._tools_cache: List[Tool] = []
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize MCP client"""
        if not MCP_ADAPTERS_AVAILABLE:
            self._initialized = False
            return
        try:
            # Build servers config expected by MultiServerMCPClient
            servers: Dict[str, Dict[str, Any]] = {}
            for name, conf in (settings.mcp_servers or {}).items():
                server_conf = dict(conf)
                # Default to streamable_http if not provided
                server_conf.setdefault("transport", "streamable_http")
                servers[name] = server_conf

            self.client = MultiServerMCPClient(servers)
            self._initialized = True
            logger.info("MCP client initialized with %d server(s)", len(servers))
        except Exception as e:
            logger.error("Failed to initialize MCP client: %s", e)
            self._initialized = False
    
    async def get_tools(self) -> List[Tool]:
        """Fetch MCP tools from all configured servers.

        Returns cached tools if already fetched successfully.
        """
        if not self._initialized or not self.client:
            return []
        try:
            # Avoid hanging indefinitely if a remote server is slow
            tools = await asyncio.wait_for(self.client.get_tools(), timeout=5.0)
            # Cache for later synchronous access if needed
            self._tools_cache = list(tools)
            try:
                names = [getattr(t, "name", "?") for t in tools]
            except Exception:
                names = []
            logger.info("Fetched %d MCP tool(s): %s", len(tools), names)
            return tools
        except Exception as e:
            logger.error("Failed to fetch MCP tools: %s", e)
            return []
    
    def get_cached_tools(self) -> List[Tool]:
        """Return last fetched tools (may be empty)."""
        return list(self._tools_cache)


class MCPToolWrapper:
    """(Reserved) Wrapper for any extra conversions if needed in future."""
    
    def __init__(self, mcp_client: Any):
        self.client = mcp_client
        self.tools: List[Tool] = []