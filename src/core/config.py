"""
Core configuration management for Dylan Assistant
"""
from typing import Optional, Dict, Any, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from pathlib import Path
import os
import json


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # API Keys
    openrouter_api_key: str = Field(default="", env="OPENROUTER_API_KEY")
    amap_api_key: str = Field(default="", env="AMAP_API_KEY")
    
    # LLM Configuration
    llm_base_url: str = Field(default="https://openrouter.ai/api/v1", env="LLM_BASE_URL")
    llm_model: str = Field(default="qwen/qwen3-next-80b-a3b-instruct", env="LLM_MODEL")
    llm_temperature: float = Field(default=0.7, env="LLM_TEMPERATURE")
    llm_streaming: bool = Field(default=True, env="LLM_STREAMING")
    
    # API Server Configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_prefix: str = Field(default="/api/v1", env="API_PREFIX")
    cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    
    # MCP Configuration
    def _default_mcp_servers():
        amap_key = os.getenv("AMAP_API_KEY", "")
        if amap_key:
            return {
                "amap-amap-sse": {
                    "url": f"https://mcp.amap.com/sse?key={amap_key}"
                }
            }
        return {}
    
    mcp_servers: Dict[str, Dict[str, Any]] = Field(
        default_factory=_default_mcp_servers,
        env="MCP_SERVERS",
    )

    @field_validator("mcp_servers", mode="before")
    @classmethod
    def _coerce_mcp_servers(cls, value: Any) -> Dict[str, Dict[str, Any]]:
        """Allow multiple input shapes:
        - JSON string
        - Mapping already
        - Mapping wrapped under key 'mcpServers'
        - Fallback to env var MCP_CONFIG if present and value is empty
        """
        # If empty, try fallback env var that may contain the provided JSON structure
        if not value:
            raw = os.getenv("MCP_CONFIG") or os.getenv("MCP_SERVERS_JSON")
            if raw:
                value = raw

        # Parse JSON string to object
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except Exception:
                return {}

        # Unwrap if nested under 'mcpServers'
        if isinstance(value, dict) and "mcpServers" in value:
            value = value.get("mcpServers") or {}

        # Ensure final type is a dict[str, dict]
        if isinstance(value, dict):
            return {str(k): (dict(v) if isinstance(v, dict) else {}) for k, v in value.items()}
        return {}
    
    # Application Settings
    app_name: str = Field(default="Dylan Assistant", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Workflow Settings
    max_iterations: int = Field(default=10, env="MAX_ITERATIONS")
    recursion_limit: int = Field(default=25, env="RECURSION_LIMIT")
    
    # Pydantic v2 settings configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore unknown environment variables
    )


# Global settings instance
settings = Settings()