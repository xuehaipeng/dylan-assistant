"""
MCP (Model Context Protocol) integration using mcp-use
"""
import asyncio
from typing import Dict, Any, List, Optional
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
import logging

from src.core.config import settings

logger = logging.getLogger(__name__)

# Optional import of mcp_use; tolerate incompatibilities gracefully
try:
    from mcp_use import MCPClient, MCPAgent  # type: ignore
    MCP_USE_AVAILABLE = True
except Exception as import_error:  # broad to catch transitive import errors
    MCP_USE_AVAILABLE = False
    logger.warning(
        "MCP integration disabled: failed to import mcp_use (%s). The server will run without MCP tools.",
        import_error,
    )


class MCPToolManager:
    """Manager for MCP tools integration"""
    
    def __init__(self):
        # Use loose typing to avoid referencing missing symbols at runtime
        self.client: Optional[Any] = None
        self.agent: Optional[Any] = None
        self._initialized = False
        self._tools: List[Tool] = []
        self._initialize()
    
    def _initialize(self):
        """Initialize MCP client and agent"""
        if not MCP_USE_AVAILABLE:
            self._initialized = False
            return
        try:
            # Create MCP client from configuration
            config = {
                "mcpServers": settings.mcp_servers
            }
            
            self.client = MCPClient.from_dict(config)
            
            # Create LLM for MCP agent
            llm = ChatOpenAI(
                base_url=settings.llm_base_url,
                model=settings.llm_model,
                api_key=settings.openrouter_api_key
            )
            
            # Create MCP agent
            self.agent = MCPAgent(
                llm=llm,
                client=self.client,
                max_steps=30
            )
            
            # Convert MCP tools to LangChain tools
            self._create_langchain_tools()
            
            self._initialized = True
            logger.info("MCP integration initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP: {e}")
            self._initialized = False
    
    def _create_langchain_tools(self):
        """Create LangChain tools from MCP capabilities"""
        if not self.client:
            return
        
        # Create AMap/高德地图 travel tool
        amap_tool = Tool(
            name="amap_travel",
            description="Query travel routes, transportation options, and navigation using AMap (高德地图). Useful for checking train schedules, routes, and travel planning in China.",
            func=self._sync_amap_query,
            coroutine=self._async_amap_query
        )
        self._tools.append(amap_tool)
        
        # Add more MCP-based tools as needed
        logger.info(f"Created {len(self._tools)} MCP-based tools")
    
    async def _async_amap_query(self, query: str) -> str:
        """Async query to AMap service via MCP"""
        if not self.agent:
            return "MCP agent not initialized"
        
        try:
            result = await self.agent.run(query)
            return str(result)
        except Exception as e:
            logger.error(f"AMap query failed: {e}")
            return f"Error querying AMap: {str(e)}"
    
    def _sync_amap_query(self, query: str) -> str:
        """Sync wrapper for AMap query"""
        try:
            loop = asyncio.get_running_loop()
            # If we're in an async context, we can't use asyncio.run()
            return "Sync execution not supported in async context. Use async version."
        except RuntimeError:
            # No running loop, safe to use asyncio.run()
            return asyncio.run(self._async_amap_query(query))
    
    def get_tools(self) -> List[Tool]:
        """Get all MCP-based tools"""
        return self._tools
    
    async def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """Execute a specific MCP tool"""
        if not self._initialized:
            raise RuntimeError("MCP not initialized")
        
        # Find and execute the tool
        for tool in self._tools:
            if tool.name == tool_name:
                if tool.coroutine:
                    return await tool.coroutine(**args)
                else:
                    return tool.func(**args)
        
        raise ValueError(f"Tool {tool_name} not found")
    
    async def query(self, message: str) -> str:
        """Direct query using MCP agent"""
        if not self.agent:
            return "MCP agent not available"
        
        try:
            result = await self.agent.run(message)
            return str(result)
        except Exception as e:
            logger.error(f"MCP query failed: {e}")
            return f"Error: {str(e)}"


class MCPToolWrapper:
    """Wrapper to convert MCP tools to LangChain-compatible tools"""
    
    def __init__(self, mcp_client: Any):
        self.client = mcp_client
        self.tools = self._create_tools()
    
    def _create_tools(self) -> List[Tool]:
        """Create LangChain tools from MCP client"""
        tools = []
        
        # This would dynamically create tools based on MCP server capabilities
        # For now, we'll create specific tools for known services
        
        return tools