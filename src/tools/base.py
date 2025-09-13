"""
Base tool definitions and registry
"""
from typing import List, Dict, Any, Optional
from langchain_core.tools import Tool, StructuredTool
from langchain_community.tools import DuckDuckGoSearchRun
from pydantic import BaseModel, Field
import httpx
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class WeatherInput(BaseModel):
    """Input for weather tool"""
    location: str = Field(description="Location for weather forecast (city name or coordinates)")


class SearchInput(BaseModel):
    """Input for search tool"""
    query: str = Field(description="Search query")
    max_results: int = Field(default=5, description="Maximum number of results")


async def get_weather(location: str) -> str:
    """
    Get weather information for a location
    
    Args:
        location: City name or coordinates
        
    Returns:
        Weather information as string
    """
    try:
        # Using a free weather API (you can replace with your preferred service)
        async with httpx.AsyncClient() as client:
            # Using wttr.in for simple weather (no API key needed)
            response = await client.get(
                f"https://wttr.in/{location}?format=j1",
                timeout=httpx.Timeout(10.0, connect=5.0)
            )
            
            if response.status_code == 200:
                data = response.json()
                current = data.get("current_condition", [{}])[0]
                
                result = f"Weather in {location}:\n"
                result += f"Temperature: {current.get('temp_C', 'N/A')}°C\n"
                result += f"Feels like: {current.get('FeelsLikeC', 'N/A')}°C\n"
                result += f"Weather: {current.get('weatherDesc', [{}])[0].get('value', 'N/A')}\n"
                result += f"Humidity: {current.get('humidity', 'N/A')}%\n"
                result += f"Wind: {current.get('windspeedKmph', 'N/A')} km/h"
                
                return result
            else:
                return f"Could not get weather for {location}"
                
    except Exception as e:
        logger.error(f"Weather API error: {e}")
        return f"Error getting weather: {str(e)}"


def search_web(query: str, max_results: int = 5) -> str:
    """
    Search the web using DuckDuckGo
    
    Args:
        query: Search query
        max_results: Maximum number of results
        
    Returns:
        Search results as string
    """
    try:
        search = DuckDuckGoSearchRun()
        results = search.run(query)
        return results
    except Exception as e:
        logger.error(f"Search error: {e}")
        return f"Error searching: {str(e)}"


async def get_current_time(timezone: Optional[str] = None) -> str:
    """
    Get current time
    
    Args:
        timezone: Optional timezone (default: UTC)
        
    Returns:
        Current time as string
    """
    from zoneinfo import ZoneInfo
    
    try:
        if timezone:
            tz = ZoneInfo(timezone)
        else:
            tz = ZoneInfo("UTC")
        
        now = datetime.now(tz)
        return f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}"
    except Exception as e:
        # Fallback to UTC
        now = datetime.utcnow()
        return f"Current time (UTC): {now.strftime('%Y-%m-%d %H:%M:%S')}"


async def calculate(expression: str) -> str:
    """
    Simple calculator for mathematical expressions
    
    Args:
        expression: Mathematical expression to evaluate
        
    Returns:
        Calculation result as string
    """
    try:
        # Safe evaluation of mathematical expressions
        import ast
        import operator
        
        # Supported operators
        ops = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
        }
        
        def eval_expr(node):
            if isinstance(node, ast.Constant):  # Modern way (Python 3.8+)
                if isinstance(node.value, (int, float)):
                    return node.value
                raise TypeError(f"Unsupported constant type {type(node.value)}")
            elif isinstance(node, ast.Num):  # Backward compatibility
                return node.n
            elif isinstance(node, ast.BinOp):
                return ops[type(node.op)](eval_expr(node.left), eval_expr(node.right))
            elif isinstance(node, ast.UnaryOp):
                return ops[type(node.op)](eval_expr(node.operand))
            else:
                raise TypeError(f"Unsupported type {type(node)}")
        
        tree = ast.parse(expression, mode='eval')
        result = eval_expr(tree.body)
        return f"{expression} = {result}"
        
    except Exception as e:
        return f"Error calculating: {str(e)}"


def _sync_wrapper(coro_func, *arg_names: str):
    """Create a sync wrapper around an async coroutine to satisfy Tool.func."""
    import inspect
    import asyncio

    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_running_loop()
            # Running inside an event loop: instruct to use coroutine path
            return "This tool must be called asynchronously."
        except RuntimeError:
            # No event loop, safe to run
            return asyncio.run(coro_func(*args, **kwargs))

    # Preserve signature for better tool arg help (optional)
    try:
        wrapper.__signature__ = inspect.signature(coro_func)  # type: ignore[attr-defined]
    except Exception:
        pass
    return wrapper


def get_all_tools() -> List[Tool]:
    """
    Get all available tools
    
    Returns:
        List of LangChain tools
    """
    tools = []
    
    # Weather tool
    weather_tool = Tool(
        name="weather",
        description="Get current weather information for a location. Input should be a city name or coordinates.",
        func=_sync_wrapper(get_weather, "location"),
        coroutine=get_weather
    )
    tools.append(weather_tool)
    
    # Search tool
    search_tool = Tool(
        name="search",
        description="Search the web for information. Useful for current events, facts, and general knowledge.",
        func=search_web
    )
    tools.append(search_tool)
    
    # Time tool
    time_tool = Tool(
        name="current_time",
        description="Get the current time. Optionally specify a timezone like 'Asia/Shanghai' or 'America/New_York'.",
        func=_sync_wrapper(get_current_time, "timezone"),
        coroutine=get_current_time
    )
    tools.append(time_tool)
    
    # Calculator tool
    calc_tool = Tool(
        name="calculator",
        description="Calculate mathematical expressions. Input should be a valid mathematical expression like '2 + 2' or '10 * 5'.",
        func=_sync_wrapper(calculate, "expression"),
        coroutine=calculate
    )
    tools.append(calc_tool)
    
    logger.info(f"Loaded {len(tools)} native tools")
    return tools


# Tool registry for easy access
TOOL_REGISTRY: Dict[str, Tool] = {
    tool.name: tool for tool in get_all_tools()
}