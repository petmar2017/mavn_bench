"""Central configuration management for Mavn Bench"""

import os
from typing import Dict, Any, Optional, List
from pathlib import Path
import yaml
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache

class StorageConfig(BaseSettings):
    type: str = Field(default="redis", env="STORAGE_TYPE")
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    filesystem_path: str = Field(default="./document_store", env="FILESYSTEM_PATH")

class DatabaseConfig(BaseSettings):
    type: str = Field(default="sqlite", env="DB_TYPE")
    sqlite_path: str = Field(default="./data/mavn_bench.db", env="SQLITE_PATH")
    postgres_url: str = Field(default="postgresql://user:pass@localhost/mavn_bench", env="POSTGRES_URL")

class AuthConfig(BaseSettings):
    provider: str = Field(default="internal", env="AUTH_PROVIDER")
    api_key_header: str = Field(default="X-API-Key", env="API_KEY_HEADER")
    test_api_key: str = Field(default="test_api_key_123456", env="TEST_API_KEY")
    test_user: str = Field(default="test_user", env="TEST_USER")

class ModelProviderConfig(BaseSettings):
    """Configuration for a specific model provider"""
    name: str
    enabled: bool = True
    model_id: str
    max_tokens: int = 2000
    temperature: float = 0.3
    # Cost configuration
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    cost_tier: str = "standard"  # economy, standard, premium
    # Performance configuration
    avg_latency_ms: int = 1000
    max_context: int = 4096
    quality_score: float = 0.8  # 0.0 to 1.0
    # Capabilities (comma-separated string)
    capabilities: str = "text_generation"
    # Task preferences (comma-separated string)
    preferred_for: str = ""  # e.g., "summarization,classification"

class LLMConfig(BaseSettings):
    # API Keys
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    google_api_key: Optional[str] = Field(default=None, env="GOOGLE_API_KEY")
    xai_api_key: Optional[str] = Field(default=None, env="XAI_API_KEY")

    # Default provider selection
    default_provider: str = Field(default="anthropic-claude-3.5-sonnet", env="LLM_DEFAULT_PROVIDER")

    # Model selection strategy: "cost", "quality", "latency", "manual"
    selection_strategy: str = Field(default="quality", env="LLM_SELECTION_STRATEGY")

    # Model provider configurations (can be extended via environment or config files)
    providers: Dict[str, Dict[str, Any]] = Field(default_factory=lambda: {
        "anthropic-claude-3.5-sonnet": {
            "name": "Claude 3.5 Sonnet",
            "enabled": True,
            "provider": "anthropic",
            "model_id": "claude-3-5-sonnet-20241022",
            "max_tokens": 4000,
            "temperature": 0.3,
            "cost_per_1k_input": 0.003,
            "cost_per_1k_output": 0.015,
            "cost_tier": "premium",
            "avg_latency_ms": 2000,
            "max_context": 200000,
            "quality_score": 0.95,
            "capabilities": "text_generation,long_context,json_mode",
            "preferred_for": "complex_reasoning,detailed_analysis,creative_writing"
        },
        "anthropic-claude-3.5-haiku": {
            "name": "Claude 3.5 Haiku",
            "enabled": True,
            "provider": "anthropic",
            "model_id": "claude-3-5-haiku-20241022",
            "max_tokens": 1000,
            "temperature": 0.3,
            "cost_per_1k_input": 0.0008,
            "cost_per_1k_output": 0.004,
            "cost_tier": "economy",
            "avg_latency_ms": 500,
            "max_context": 200000,
            "quality_score": 0.85,
            "capabilities": "text_generation,fast_inference,long_context",
            "preferred_for": "summarization,classification,quick_tasks"
        },
        "openai-gpt-4o": {
            "name": "GPT-4 Optimized",
            "enabled": True,
            "provider": "openai",
            "model_id": "gpt-4o",
            "max_tokens": 4000,
            "temperature": 0.3,
            "cost_per_1k_input": 0.005,
            "cost_per_1k_output": 0.015,
            "cost_tier": "premium",
            "avg_latency_ms": 1500,
            "max_context": 128000,
            "quality_score": 0.93,
            "capabilities": "text_generation,function_calling,vision,json_mode",
            "preferred_for": "code_generation,function_calling,multimodal"
        },
        "openai-gpt-4o-mini": {
            "name": "GPT-4 Mini",
            "enabled": True,
            "provider": "openai",
            "model_id": "gpt-4o-mini",
            "max_tokens": 2000,
            "temperature": 0.3,
            "cost_per_1k_input": 0.00015,
            "cost_per_1k_output": 0.0006,
            "cost_tier": "economy",
            "avg_latency_ms": 800,
            "max_context": 128000,
            "quality_score": 0.80,
            "capabilities": "text_generation,fast_inference,function_calling",
            "preferred_for": "simple_tasks,high_volume,cost_sensitive"
        },
        "google-gemini-1.5-pro": {
            "name": "Gemini 1.5 Pro",
            "enabled": False,  # Disabled by default until API key provided
            "provider": "google",
            "model_id": "gemini-1.5-pro",
            "max_tokens": 8192,
            "temperature": 0.3,
            "cost_per_1k_input": 0.00125,
            "cost_per_1k_output": 0.005,
            "cost_tier": "standard",
            "avg_latency_ms": 1200,
            "max_context": 2000000,  # 2M context window
            "quality_score": 0.90,
            "capabilities": "text_generation,vision,long_context,batch",
            "preferred_for": "document_analysis,multimodal,very_long_context"
        },
        "google-gemini-1.5-flash": {
            "name": "Gemini 1.5 Flash",
            "enabled": False,
            "provider": "google",
            "model_id": "gemini-1.5-flash",
            "max_tokens": 8192,
            "temperature": 0.3,
            "cost_per_1k_input": 0.00025,
            "cost_per_1k_output": 0.001,
            "cost_tier": "economy",
            "avg_latency_ms": 400,
            "max_context": 1000000,  # 1M context window
            "quality_score": 0.82,
            "capabilities": "text_generation,fast_inference,vision,long_context",
            "preferred_for": "high_volume,fast_response,cost_optimization"
        },
        "xai-grok-beta": {
            "name": "Grok Beta",
            "enabled": False,  # Coming soon
            "provider": "xai",
            "model_id": "grok-beta",
            "max_tokens": 4000,
            "temperature": 0.3,
            "cost_per_1k_input": 0.005,
            "cost_per_1k_output": 0.015,
            "cost_tier": "premium",
            "avg_latency_ms": 1800,
            "max_context": 128000,
            "quality_score": 0.88,
            "capabilities": "text_generation,function_calling",
            "preferred_for": "reasoning,analysis"
        },
        "openai-text-embedding-3-small": {
            "name": "Text Embedding 3 Small",
            "enabled": True,
            "provider": "openai",
            "model_id": "text-embedding-3-small",
            "max_tokens": 8191,
            "cost_per_1k_input": 0.00002,
            "cost_per_1k_output": 0.0,
            "cost_tier": "economy",
            "avg_latency_ms": 100,
            "max_context": 8191,
            "quality_score": 0.85,
            "capabilities": "embeddings",
            "preferred_for": "semantic_search,similarity"
        },
        "openai-text-embedding-3-large": {
            "name": "Text Embedding 3 Large",
            "enabled": True,
            "provider": "openai",
            "model_id": "text-embedding-3-large",
            "max_tokens": 8191,
            "cost_per_1k_input": 0.00013,
            "cost_per_1k_output": 0.0,
            "cost_tier": "standard",
            "avg_latency_ms": 150,
            "max_context": 8191,
            "quality_score": 0.95,
            "capabilities": "embeddings",
            "preferred_for": "high_quality_search,rag"
        }
    })

    # Task-specific model selection overrides
    task_model_overrides: Dict[str, str] = Field(default_factory=lambda: {
        "summarization": "anthropic-claude-3.5-haiku",
        "entity_extraction": "openai-gpt-4o-mini",
        "classification": "anthropic-claude-3.5-haiku",
        "embeddings": "openai-text-embedding-3-small",
        "complex_reasoning": "anthropic-claude-3.5-sonnet",
        "code_generation": "openai-gpt-4o",
        "vision_tasks": "google-gemini-1.5-pro"
    })

    # Fallback chain when preferred model unavailable
    fallback_chain: List[str] = Field(default_factory=lambda: [
        "anthropic-claude-3.5-sonnet",
        "openai-gpt-4o",
        "anthropic-claude-3.5-haiku",
        "openai-gpt-4o-mini"
    ])


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

class PaginationConfig(BaseSettings):
    """Pagination settings"""
    default_limit: int = Field(default=20, env="PAGINATION_DEFAULT_LIMIT")
    max_limit: int = Field(default=100, env="PAGINATION_MAX_LIMIT")
    default_sort_by: str = Field(default="updated_at", env="PAGINATION_DEFAULT_SORT_BY")
    default_sort_order: str = Field(default="desc", env="PAGINATION_DEFAULT_SORT_ORDER")

class QueueConfig(BaseSettings):
    """Queue settings for document processing"""
    backend: str = Field(default="redis", env="QUEUE_BACKEND", description="Queue backend: 'redis' or 'memory'")
    max_concurrent_workers: int = Field(default=3, env="QUEUE_MAX_WORKERS")
    processing_timeout: int = Field(default=300, env="QUEUE_PROCESSING_TIMEOUT", description="Processing timeout in seconds")
    retry_max_attempts: int = Field(default=3, env="QUEUE_RETRY_MAX_ATTEMPTS")
    stale_job_check_interval: int = Field(default=60, env="QUEUE_STALE_JOB_CHECK_INTERVAL", description="Check for stale jobs every N seconds")

class Settings(BaseSettings):
    app_name: str = Field(default="Mavn Bench", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    # Log level is handled directly in logger.py, but we need to accept it here
    # to avoid Pydantic validation errors when it's in the environment
    mavn_log_level: Optional[str] = Field(default="INFO", env="MAVN_LOG_LEVEL")

    storage: StorageConfig = Field(default_factory=StorageConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)
    pagination: PaginationConfig = Field(default_factory=PaginationConfig)
    queue: QueueConfig = Field(default_factory=QueueConfig)
    
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
