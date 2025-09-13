#!/usr/bin/env python
"""
Start the Dylan Assistant API server
"""
import uvicorn
import logging
from src.core.config import settings

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

if __name__ == "__main__":
    print(f"""
    ╔══════════════════════════════════════════╗
    ║         Dylan Assistant v{settings.app_version}         ║
    ║     AI Assistant with LangGraph & MCP     ║
    ╚══════════════════════════════════════════╝
    
    Starting API server on http://{settings.api_host}:{settings.api_port}
    Documentation: http://{settings.api_host}:{settings.api_port}/docs
    Health check: http://{settings.api_host}:{settings.api_port}/health
    """)
    
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )