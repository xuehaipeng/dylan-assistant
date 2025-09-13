"""
Agent state definitions for LangGraph workflows
"""
from typing import List, Dict, Any, Optional, Annotated, TypedDict, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import add_messages
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class MessageState(TypedDict):
    """State for message-based workflows"""
    messages: Annotated[Sequence[BaseMessage], add_messages]


class AgentState(TypedDict):
    """Main agent state for the assistant workflow"""
    messages: Annotated[List[BaseMessage], add_messages]
    current_step: int
    max_steps: int
    user_input: str
    context: Dict[str, Any]
    tools_output: List[Dict[str, Any]]
    final_answer: Optional[str]
    error: Optional[str]
    metadata: Dict[str, Any]


class StreamingState(TypedDict):
    """State for streaming responses"""
    messages: Annotated[List[BaseMessage], add_messages]
    streaming_content: str
    is_complete: bool
    tool_calls: List[Dict[str, Any]]
    current_node: str


class IntentType(str, Enum):
    """Types of user intents"""
    TRAVEL = "travel"
    WEATHER = "weather"
    SEARCH = "search"
    GENERAL = "general"
    TOOL_USE = "tool_use"
    CLARIFICATION = "clarification"


class ToolCall(BaseModel):
    """Tool call representation"""
    tool_name: str
    arguments: Dict[str, Any]
    call_id: str
    result: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ConversationContext(BaseModel):
    """Conversation context tracking"""
    session_id: str
    user_id: Optional[str] = None
    conversation_history: List[BaseMessage] = Field(default_factory=list)
    context_variables: Dict[str, Any] = Field(default_factory=dict)
    intent: Optional[IntentType] = None
    language: str = "zh"  # Default to Chinese based on test.py
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)