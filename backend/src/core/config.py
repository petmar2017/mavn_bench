"""Central configuration management for Mavn Bench"""

import os
from typing import Dict, Any, Optional, List
from pathlib import Path
import yaml
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache

class StorageConfig(BaseSettings):
    type: str = Field(default="filesystem", env="STORAGE_TYPE")
    filesystem_base_path: str = Field(default="/document_store", env="FILESYSTEM_BASE_PATH")
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")

class DatabaseConfig(BaseSettings):
    type: str = Field(default="sqlite", env="DB_TYPE")
    sqlite_path: str = Field(default="./data/mavn_bench.db", env="SQLITE_PATH")
    postgres_url: str = Field(default="postgresql://user:pass@localhost/mavn_bench", env="POSTGRES_URL")

class AuthConfig(BaseSettings):
    provider: str = Field(default="internal", env="AUTH_PROVIDER")
    api_key_header: str = Field(default="X-API-Key", env="API_KEY_HEADER")
    test_api_key: str = Field(default="test_api_key_123456", env="TEST_API_KEY")
    test_user: str = Field(default="test_user", env="TEST_USER")

class LLMConfig(BaseSettings):
    # API Keys
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")

    # Default provider (claude is default)
    default_provider: str = Field(default="anthropic", env="LLM_DEFAULT_PROVIDER")

    # Claude/Anthropic settings
    claude_model: str = Field(default="claude-3-5-sonnet-20241022", env="LLM_CLAUDE_MODEL")
    claude_max_tokens: int = Field(default=4000, env="LLM_CLAUDE_MAX_TOKENS")
    claude_temperature: float = Field(default=0.3, env="LLM_CLAUDE_TEMPERATURE")

    # OpenAI settings
    openai_model: str = Field(default="gpt-4o", env="LLM_OPENAI_MODEL")
    openai_max_tokens: int = Field(default=2000, env="LLM_OPENAI_MAX_TOKENS")
    openai_temperature: float = Field(default=0.3, env="LLM_OPENAI_TEMPERATURE")

    # Default settings (uses Claude values by default)
    default_model: str = Field(default="claude-3-5-sonnet-20241022", env="LLM_DEFAULT_MODEL")
    max_tokens: int = Field(default=4000, env="LLM_MAX_TOKENS")
    temperature: float = Field(default=0.3, env="LLM_TEMPERATURE")

    # PDF processing settings
    pdf_use_ai: bool = Field(default=True, env="PDF_USE_AI", description="Use Claude AI for PDF processing")
    pdf_prefer_pymupdf: bool = Field(default=True, env="PDF_PREFER_PYMUPDF", description="Prefer PyMuPDF over Claude AI when available")

class MCPConfig(BaseSettings):
    enabled: bool = Field(default=True, env="MCP_ENABLED")
    servers: List[Dict[str, Any]] = Field(default_factory=list)

class TelemetryConfig(BaseSettings):
    enabled: bool = Field(default=True, env="TELEMETRY_ENABLED")
    service_name: str = Field(default="mavn-bench-backend", env="SERVICE_NAME")
    otlp_endpoint: str = Field(default="http://localhost:4317", env="OTEL_EXPORTER_OTLP_ENDPOINT")
    jaeger_endpoint: str = Field(default="http://localhost:14268/api/traces", env="JAEGER_ENDPOINT")

class Settings(BaseSettings):
    app_name: str = Field(default="Mavn Bench", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    storage: StorageConfig = Field(default_factory=StorageConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)
    
    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"

    @classmethod
    def load_from_yaml(cls, yaml_path: Optional[str] = None) -> "Settings":
        """Load settings from YAML file with environment overrides"""
        if yaml_path and Path(yaml_path).exists():
            with open(yaml_path, 'r') as f:
                config_data = yaml.safe_load(f)
                return cls(**config_data)
        return cls()

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    yaml_path = os.getenv("CONFIG_PATH", "./config/settings.yaml")
    return Settings.load_from_yaml(yaml_path)
