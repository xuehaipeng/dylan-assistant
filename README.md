# Dylan Assistant

An AI-powered assistant built with LangGraph, LangChain, and MCP (Model Context Protocol) support, featuring HTTP SSE streaming for real-time responses.

## 🚀 Features

- **Streaming API with SSE**: Real-time streaming responses via Server-Sent Events
- **LangGraph Orchestration**: State-based workflow management for complex conversations
- **MCP Integration**: Support for Model Context Protocol tools (AMap/高德地图 for travel queries)
- **Multiple Tools**: Weather, search, calculator, time, and more
- **Async Architecture**: High-performance async/await throughout
- **OpenRouter Support**: Use any LLM model available on OpenRouter

## 📋 Prerequisites

- Python 3.11+
- OpenRouter API key (get one at https://openrouter.ai)

## 🛠️ Installation

1. Clone the repository:
```bash
cd dylan-assistant
```

2. Install dependencies:
```bash
conda activate dylan-assistant
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
# Copy the existing .env file (already contains your API key)
# Or create a new one:
echo "OPENROUTER_API_KEY=your_key_here" > .env
```

## 🚀 Quick Start

### Start the API Server

```bash
python run_server.py
```

The server will start on `http://localhost:8000`

- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### Test with Example Client

```bash
# Test streaming chat (Chinese query for trains)
python examples/client_example.py -m "帮我查一下北京到上海的高铁"

# Test weather query
python examples/client_example.py -m "What's the weather in Beijing?"

# Test search
python examples/client_example.py -m "Search for Python tutorials"

# Test calculator
python examples/client_example.py -m "Calculate 123 * 456"
```

### Run Test Suite

```bash
python test_assistant.py
```

## 📡 API Endpoints

### Chat with Streaming (SSE)

**POST** `/api/v1/chat`

```json
{
  "message": "Your question here",
  "stream": true,
  "session_id": "optional-session-id"
}
```

Returns Server-Sent Events stream with:
- `token`: Streaming text tokens
- `tool_start`: Tool execution started
- `tool_end`: Tool execution completed
- `done`: Stream complete

### Chat without Streaming

**POST** `/api/v1/chat`

```json
{
  "message": "Your question here",
  "stream": false
}
```

Returns complete response:
```json
{
  "response": "Assistant response",
  "session_id": "session-id",
  "metadata": {}
}
```

## 🧰 Available Tools

1. **AMap Travel** (via MCP): Query train schedules, routes, and travel planning in China
2. **Weather**: Get weather information for any location
3. **Web Search**: Search the web using DuckDuckGo
4. **Calculator**: Evaluate mathematical expressions
5. **Current Time**: Get current time in any timezone

## 🏗️ Project Structure

```
dylan-assistant/
├── src/
│   ├── api/              # FastAPI application with SSE
│   ├── core/             # Configuration and state management
│   ├── workflows/        # LangGraph workflow definitions
│   ├── tools/            # Tool implementations
│   └── integrations/     # MCP and external integrations
├── examples/             # Example client implementations
├── test_assistant.py     # Test suite
├── run_server.py        # Server startup script
└── requirements.txt     # Dependencies
```

## 🔧 Configuration

Environment variables (`.env`):

```env
# API Keys
OPENROUTER_API_KEY=your_key_here
AMAP_API_KEY=your_amap_api_key

# LLM Settings
LLM_MODEL=qwen/qwen3-next-80b-a3b-instruct
LLM_TEMPERATURE=0.7
LLM_STREAMING=true

# Server Settings
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
LOG_LEVEL=INFO
```

## 🧪 Testing

### Using curl

```bash
# Test SSE streaming
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "stream": true}' \
  -H "Accept: text/event-stream"

# Test non-streaming
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "stream": false}'
```

### Using Python

```python
import httpx
from httpx_sse import aconnect_sse

async def test_streaming():
    async with httpx.AsyncClient() as client:
        async with aconnect_sse(
            client, "POST", 
            "http://localhost:8000/api/v1/chat",
            json={"message": "Hello", "stream": True}
        ) as event_source:
            async for sse in event_source.aiter_sse():
                print(f"Event: {sse.event}, Data: {sse.data}")
```

## 🎯 Use Cases

- **Travel Planning**: Query train schedules, routes, and transportation options in China
- **Weather Queries**: Get current weather and forecasts for any location
- **Information Search**: Search the web for current information
- **Calculations**: Perform mathematical calculations
- **General Q&A**: Answer general questions using the LLM

## 📊 Performance

- Streaming responses start in < 1 second
- Tool execution typically completes in 1-3 seconds
- Supports multiple concurrent sessions
- Memory-efficient streaming with SSE

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Add new tools
- Improve workflows
- Enhance streaming performance
- Add more MCP integrations

## 📄 License

MIT License

## 🆘 Support

For issues or questions:
- Check the API documentation at `/docs`
- Run the test suite: `python test_assistant.py`
- Review logs for debugging

## 🎉 Acknowledgments

- Built with [LangChain](https://langchain.com/) and [LangGraph](https://github.com/langchain-ai/langgraph)
- MCP support via [mcp-use](https://github.com/mcp-use/mcp-use)
- Powered by OpenRouter and various LLM providers