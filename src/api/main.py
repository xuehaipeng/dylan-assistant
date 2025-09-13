"""
FastAPI application with SSE streaming support
"""
import json
import asyncio
import uuid
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel, Field, field_validator
import logging

from src.core.config import settings
from src.workflows.assistant import AssistantWorkflow
from src.core.state import ConversationContext

logger = logging.getLogger(__name__)

# Global workflow instance
workflow: Optional[AssistantWorkflow] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global workflow
    logger.info("Starting Dylan Assistant API...")
    
    # Initialize workflow (tolerate missing/invalid LLM configuration)
    try:
        workflow = AssistantWorkflow()
    except Exception as e:
        logger.error(f"Failed to initialize AssistantWorkflow: {e}")
        workflow = None
    
    yield
    
    # Cleanup
    logger.info("Shutting down Dylan Assistant API...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class ChatRequest(BaseModel):
    """Chat request model"""
    message: str = Field(..., description="User message", min_length=1, max_length=8000)
    session_id: Optional[str] = Field(default=None, description="Session ID for conversation history", max_length=100)
    stream: bool = Field(default=True, description="Enable streaming response")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    
    @field_validator('message')
    @classmethod
    def validate_message(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Message cannot be empty or contain only whitespace")
        return v.strip()


class ChatResponse(BaseModel):
    """Chat response model"""
    response: str = Field(..., description="Assistant response")
    session_id: str = Field(..., description="Session ID")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Response metadata")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(default="healthy")
    version: str = Field(default=settings.app_version)
    model: str = Field(default=settings.llm_model)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "openapi": "/openapi.json"
    }


@app.post(f"{settings.api_prefix}/chat")
async def chat(request: ChatRequest):
    """
    Chat endpoint with optional streaming
    
    For streaming responses, returns Server-Sent Events (SSE)
    For non-streaming, returns complete response
    """
    if not workflow:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    # Generate session ID if not provided
    session_id = request.session_id or str(uuid.uuid4())
    
    if request.stream:
        # Return SSE stream
        return EventSourceResponse(
            stream_chat_response(request.message, session_id),
            media_type="text/event-stream"
        )
    else:
        # Return complete response
        try:
            response = await workflow.get_response(request.message, session_id)
            return ChatResponse(
                response=response,
                session_id=session_id,
                metadata={"stream": False}
            )
        except Exception as e:
            logger.error(f"Chat error: {e}")
            raise HTTPException(status_code=500, detail=str(e))


async def stream_chat_response(message: str, session_id: str):
    """
    Stream chat response as Server-Sent Events
    
    Event types:
    - token: Streaming text token
    - tool_start: Tool execution started
    - tool_end: Tool execution completed
    - error: Error occurred
    - done: Stream complete
    """
    try:
        buffer = []
        
        async for chunk in workflow.run(message, session_id):
            event_type = chunk["type"]
            
            if event_type == "token":
                # Stream text token
                content = chunk["content"]
                buffer.append(content)
                
                yield {
                    "event": "token",
                    "data": json.dumps({
                        "content": content,
                        "accumulated": "".join(buffer)
                    })
                }
            
            elif event_type == "tool_start":
                # Tool execution started
                yield {
                    "event": "tool_start",
                    "data": json.dumps({
                        "tool": chunk["tool"],
                        "args": chunk.get("args", {})
                    })
                }
            
            elif event_type == "tool_end":
                # Tool execution completed
                yield {
                    "event": "tool_end",
                    "data": json.dumps({
                        "tool": chunk["tool"],
                        "result": chunk.get("result", {})
                    })
                }
            
            elif event_type == "error":
                # Error occurred
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "error": chunk["error"]
                    })
                }
                break
        
        # Send completion event
        yield {
            "event": "done",
            "data": json.dumps({
                "message": "".join(buffer),
                "session_id": session_id
            })
        }
    
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        yield {
            "event": "error",
            "data": json.dumps({"error": str(e)})
        }


@app.post(f"{settings.api_prefix}/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Alternative streaming endpoint that always returns SSE
    """
    if not workflow:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    session_id = request.session_id or str(uuid.uuid4())
    
    return EventSourceResponse(
        stream_chat_response(request.message, session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Session-ID": session_id
        }
    )


@app.get(f"{settings.api_prefix}/sessions/{{session_id}}")
async def get_session(session_id: str):
    """Get session history and context"""
    # This would retrieve from a database in production
    return {
        "session_id": session_id,
        "messages": [],
        "context": {}
    }


@app.delete(f"{settings.api_prefix}/sessions/{{session_id}}")
async def clear_session(session_id: str):
    """Clear session history"""
    # This would clear from database in production
    return {"message": f"Session {session_id} cleared"}


if __name__ == "__main__":
    import uvicorn
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Run server
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower()
    )