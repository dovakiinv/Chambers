from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class AIModelConfig(BaseModel):
    enabled: bool = True
    model: str
    vendor: str  # Required for vendor boundary enforcement
    fallback: Optional[str] = None
    temperature: float = 0.7

class ContextConfig(BaseModel):
    budget_pinned: int = 15000
    budget_history: int = 20000
    budget_hot: int = 20000
    budget_on_demand: int = 5000
    auto_load: List[str] = ["plan.md", "PLANNING_FRAMEWORK.md"]

class LatencyConfig(BaseModel):
    blacksmith_timeout_ms: int = 3000
    summarize_async: bool = True

class ObservabilityConfig(BaseModel):
    enable_metrics: bool = False
    log_path: str = "~/.chambers/metrics.log"

class BlacksmithConfig(BaseModel):
    mcp_url: str = "http://localhost:8000"
    auto_index_on_write: bool = True
    enable_sentry: bool = True

class AppConfig(BaseSettings):
    app_name: str = "SKYFORGE Chambers"
    theme: str = "dark_protocol"
    
    # AI Keys (Loaded from .env)
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    xai_api_key: Optional[str] = None

    # Sub-configs
    context: ContextConfig = ContextConfig()
    latency: LatencyConfig = LatencyConfig()
    observability: ObservabilityConfig = ObservabilityConfig()
    blacksmith: BlacksmithConfig = BlacksmithConfig()
    
    # Model Definitions (Bleeding Edge 2025)
    ai_models: Dict[str, AIModelConfig] = {
        # Primary Models
        "claude": AIModelConfig(
            model="claude-sonnet-4-5-20250929", 
            vendor="anthropic", 
            fallback="claude-haiku"
        ),
        "gemini": AIModelConfig(
            model="gemini-3-pro-preview", 
            vendor="google", 
            fallback="gemini-flash"
        ),
        "grok": AIModelConfig(
            model="grok-4", 
            vendor="xai", 
            fallback=None
        ),
        
        # Fallback Models (Must be defined for validation)
        "claude-haiku": AIModelConfig(
            model="claude-haiku-4-5-20251001",
            vendor="anthropic",
            enabled=False  # Only used as fallback
        ),
        "gemini-flash": AIModelConfig(
            model="gemini-2.5-flash",
            vendor="google",
            enabled=False
        ),
    }

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Singleton instance
config = AppConfig()
