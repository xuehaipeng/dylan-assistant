"""
Main LangGraph workflow for Dylan Assistant with streaming support
"""
import json
from typing import Dict, Any, List, Optional, AsyncIterator, Literal
from langchain_core.messages import (
    BaseMessage, 
    HumanMessage, 
    AIMessage, 
    ToolMessage,
    SystemMessage
)
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import Tool
from langchain_core.runnables import RunnableConfig
import logging

from src.core.config import settings
from src.core.state import AgentState, StreamingState
from src.tools.base import get_all_tools
from src.integrations.mcp_integration import MCPToolManager

logger = logging.getLogger(__name__)


class AssistantWorkflow:
    """Main workflow for the assistant using LangGraph"""
    
    def __init__(self):
        self.llm = self._create_llm()
        self.tools = get_all_tools()
        self.mcp_manager = MCPToolManager()
        self.memory = MemorySaver()
        self.graph = None
        self._initialize_graph()
    
    def _create_llm(self) -> ChatOpenAI:
        """Create the LLM instance with streaming support"""
        if not settings.openrouter_api_key:
            raise ValueError("OpenRouter API key is required but not provided. Set OPENROUTER_API_KEY environment variable.")
        
        return ChatOpenAI(
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            api_key=settings.openrouter_api_key,
            temperature=settings.llm_temperature,
            streaming=settings.llm_streaming,
            max_retries=3
        )
    
    def _initialize_graph(self):
        """Initialize the LangGraph workflow"""
        # Create workflow graph
        workflow = StateGraph(AgentState)
        
        # Bind tools to LLM
        all_tools = self.tools + self.mcp_manager.get_tools()
        llm_with_tools = self.llm.bind_tools(all_tools)
        
        # Define nodes
        async def agent_node(state: AgentState) -> AgentState:
            """Main agent node that processes messages"""
            messages = state["messages"]
            
            # Add system prompt if this is the first message
            if len(messages) == 1:
                system_prompt = self._get_system_prompt()
                messages = [SystemMessage(content=system_prompt)] + messages
            
            # Call LLM with tools
            response = await llm_with_tools.ainvoke(messages)
            
            # Update state
            return {
                "messages": [response],
                "current_step": state.get("current_step", 0) + 1
            }
        
        async def tools_node(state: AgentState) -> AgentState:
            """Execute tools and return results"""
            messages = state["messages"]
            last_message = messages[-1]
            
            tool_calls = last_message.tool_calls
            results = []
            
            for tool_call in tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                
                # Find and execute tool
                tool = self._find_tool(tool_name)
                if tool:
                    try:
                        result = await tool.ainvoke(tool_args)
                        results.append(
                            ToolMessage(
                                content=str(result),
                                tool_call_id=tool_call["id"]
                            )
                        )
                    except TimeoutError as e:
                        logger.error(f"Tool execution timeout: {e}")
                        results.append(
                            ToolMessage(
                                content="Tool execution timed out. Please try again.",
                                tool_call_id=tool_call["id"]
                            )
                        )
                    except ValueError as e:
                        logger.error(f"Invalid tool arguments: {e}")
                        results.append(
                            ToolMessage(
                                content=f"Invalid input: {str(e)}",
                                tool_call_id=tool_call["id"]
                            )
                        )
                    except Exception as e:
                        logger.error(f"Tool execution failed: {e}", exc_info=True)
                        results.append(
                            ToolMessage(
                                content=f"Tool error: {str(e)}",
                                tool_call_id=tool_call["id"]
                            )
                        )
            
            return {"messages": results, "tools_output": results}
        
        def should_continue(state: AgentState) -> Literal["tools", "end"]:
            """Determine if we should continue or end"""
            messages = state["messages"]
            last_message = messages[-1]
            
            # Check if we've reached max steps
            if state.get("current_step", 0) >= state.get("max_steps", 10):
                return "end"
            
            # Check for tool calls
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"
            
            return "end"
        
        # Add nodes to graph
        workflow.add_node("agent", agent_node)
        workflow.add_node("tools", tools_node)
        
        # Set entry point
        workflow.set_entry_point("agent")
        
        # Add edges
        workflow.add_conditional_edges(
            "agent",
            should_continue,
            {
                "tools": "tools",
                "end": END
            }
        )
        workflow.add_edge("tools", "agent")
        
        # Compile graph with memory
        self.graph = workflow.compile(checkpointer=self.memory)
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the assistant"""
        return """You are Dylan Assistant, a helpful AI assistant that can help with various tasks including:
        - Travel planning and route information (using AMap/高德地图)
        - Weather forecasts
        - Web searches
        - General questions and conversations
        
        You have access to various tools that you can use to help answer questions.
        Always be helpful, accurate, and provide detailed responses when needed.
        Respond in the same language as the user's query.
        
        When using tools:
        1. Think about which tool would be most appropriate
        2. Use tools when they would provide valuable information
        3. Combine multiple tools if needed for comprehensive answers
        4. Explain the results clearly to the user
        """
    
    def _find_tool(self, tool_name: str) -> Optional[Tool]:
        """Find a tool by name"""
        all_tools = self.tools + self.mcp_manager.get_tools()
        for tool in all_tools:
            if tool.name == tool_name:
                return tool
        return None
    
    async def run(
        self,
        message: str,
        session_id: str = "default",
        config: Optional[RunnableConfig] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Run the workflow with streaming support
        
        Args:
            message: User message
            session_id: Session ID for conversation history
            config: Optional runtime configuration
            
        Yields:
            Stream of response chunks
        """
        # Initialize state
        initial_state = AgentState(
            messages=[HumanMessage(content=message)],
            current_step=0,
            max_steps=settings.max_iterations,
            user_input=message,
            context={},
            tools_output=[],
            final_answer=None,
            error=None,
            metadata={"session_id": session_id}
        )
        
        # Configure thread
        config = config or {}
        config["configurable"] = {"thread_id": session_id}
        
        try:
            # Stream events from the graph
            async for event in self.graph.astream_events(
                initial_state,
                config,
                version="v2"
            ):
                # Process different event types
                if event["event"] == "on_chat_model_stream":
                    # Stream token from LLM
                    content = event["data"]["chunk"].content
                    if content:
                        yield {
                            "type": "token",
                            "content": content,
                            "node": event.get("name", "agent")
                        }
                
                elif event["event"] == "on_tool_start":
                    # Tool execution started
                    yield {
                        "type": "tool_start",
                        "tool": event["name"],
                        "args": event.get("data", {}).get("input", {})
                    }
                
                elif event["event"] == "on_tool_end":
                    # Tool execution completed
                    yield {
                        "type": "tool_end",
                        "tool": event["name"],
                        "result": event.get("data", {}).get("output", {})
                    }
                
                elif event["event"] == "on_chain_end":
                    # Node completed
                    if event["name"] == "agent":
                        yield {
                            "type": "node_complete",
                            "node": "agent"
                        }
        
        except Exception as e:
            logger.error(f"Workflow execution error: {e}", exc_info=True)
            yield {
                "type": "error",
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def get_response(
        self,
        message: str,
        session_id: str = "default"
    ) -> str:
        """
        Get a complete response (non-streaming)
        
        Args:
            message: User message
            session_id: Session ID
            
        Returns:
            Complete response string
        """
        response_parts = []
        
        async for chunk in self.run(message, session_id):
            if chunk["type"] == "token":
                response_parts.append(chunk["content"])
        
        return "".join(response_parts)