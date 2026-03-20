import json
from functools import lru_cache
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "GEO Feedback Optimizer"
    APP_VERSION: str = "1.1.0"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Railway: set to postgres URL in env.
    # Local dev fallback:
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/geo_optimizer.db"

    CORS_ORIGINS: str = (
        "http://localhost:5173,"
        "http://localhost:3000,"
        "http://127.0.0.1:5173,"
        "http://127.0.0.1:3000"
    )

    # Simple internal auth for deployment.
    INTERNAL_API_KEY: Optional[str] = None

    # LLM providers.
    DEFAULT_LLM_PROVIDER: str = "zhipu"
    ZHIPU_API_KEY: Optional[str] = None
    ZHIPU_MODEL: str = "glm-4-flash"
    DOUBAO_API_KEY: Optional[str] = None
    DOUBAO_API_URL: str = "https://ark.cn-beijing.volces.com/api/v3"
    DOUBAO_MODEL: str = "ep-20241105163904-g7qlg"
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_SITE_URL: Optional[str] = None
    OPENROUTER_APP_NAME: Optional[str] = None
    OPENROUTER_MODEL: str = "openai/gpt-4o-mini"
    # Expert-grade models for deep analysis and content generation.
    OPENROUTER_ANALYSIS_MODEL: str = "anthropic/claude-sonnet-4-5"
    OPENROUTER_CONTENT_MODEL: str = "google/gemini-2.5-pro-preview"

    # Expert team model routing (via OpenRouter).
    EXPERT_STRATEGY_MODEL: str = "anthropic/claude-sonnet-4-6"
    EXPERT_CONTENT_MODEL: str = "anthropic/claude-sonnet-4-6"
    EXPERT_REVIEW_MODEL: str = "anthropic/claude-sonnet-4-6"
    EXPERT_ANALYSIS_MODEL: str = "google/gemini-3.1-pro"
    EXPERT_GEO_MODEL: str = "google/gemini-3.1-pro"

    # Feature flags.
    FEATURE_WECHAT_RICH_POST: bool = False
    FEATURE_EXPERT_TEAM: bool = True
    FEATURE_PROMPT_PROFILES: bool = True
    FEATURE_WORKFLOW_STEPS: bool = True
    FEATURE_AGENT_TEAM: bool = True

    # Storage backend.
    STORAGE_BACKEND: str = "local"  # local | s3
    UPLOAD_DIR: str = "./data/uploads"
    EXPORT_DIR: str = "./data/exports"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024

    # S3-compatible settings.
    S3_ENDPOINT_URL: Optional[str] = None
    S3_BUCKET: Optional[str] = None
    S3_ACCESS_KEY: Optional[str] = None
    S3_SECRET_KEY: Optional[str] = None
    S3_REGION: str = "auto"

    # Business constraints.
    MAX_CONTENT_PER_REQUEST: int = 10
    KEYWORD_CACHE_TTL: int = 3600

    @field_validator("DEFAULT_LLM_PROVIDER")
    @classmethod
    def validate_provider(cls, value: str) -> str:
        if value not in {"zhipu", "doubao", "openrouter"}:
            return "zhipu"
        return value

    @property
    def cors_origins_list(self) -> List[str]:
        cleaned = (self.CORS_ORIGINS or "").lstrip("\ufeff").strip()
        if not cleaned:
            return []
        if cleaned.startswith("["):
            try:
                parsed = json.loads(cleaned)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except Exception:
                pass
        return [item.strip() for item in cleaned.split(",") if item.strip()]

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def llm_key_status(self) -> dict[str, bool]:
        return {
            "zhipu": bool(self.ZHIPU_API_KEY),
            "doubao": bool(self.DOUBAO_API_KEY),
            "openrouter": bool(self.OPENROUTER_API_KEY),
        }


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
