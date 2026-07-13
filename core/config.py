"""Application configuration loaded from environment / .env.

Uses pydantic for validation so misconfiguration fails fast at startup.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator

load_dotenv()

# Directory containing this file's parent (project root).
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseModel):
    aiproxy_token: str = ""
    aiproxy_base_url: str = "https://aiproxy.sanand.workers.dev/openai/v1"
    data_dir: Path = Field(default=Path("data"))
    planner_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    fallback_planner_model: str = "gpt-4o"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    enable_llm_cache: bool = True
    max_llm_retries: int = 3
    tls_enabled: bool = False

    @model_validator(mode="after")
    def _resolve_paths(self) -> Settings:
        if not self.data_dir.is_absolute():
            self.data_dir = (BASE_DIR / self.data_dir).resolve()
        else:
            self.data_dir = self.data_dir.resolve()
        return self

    @model_validator(mode="after")
    def _require_token(self) -> Settings:
        if not self.aiproxy_token:
            raise ValueError(
                "AIPROXY_TOKEN is not set. Copy .env.example to .env and provide a token."
            )
        return self


def _build_settings() -> Settings:
    return Settings(
        aiproxy_token=os.getenv("AIPROXY_TOKEN", ""),
        aiproxy_base_url=os.getenv(
            "AIPROXY_BASE_URL", "https://aiproxy.sanand.workers.dev/openai/v1"
        ),
        data_dir=Path(os.getenv("DATA_DIR", "data")),
        planner_model=os.getenv("PLANNER_MODEL", "gpt-4o-mini"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        enable_llm_cache=os.getenv("ENABLE_LLM_CACHE", "true").lower()
        in ("1", "true", "yes", "on"),
        max_llm_retries=int(os.getenv("MAX_LLM_RETRIES", "3")),
        tls_enabled=os.getenv("TLS_ENABLED", "false").lower()
        in ("1", "true", "yes", "on"),
    )


# Instantiated once at import time; raises if AIPROXY_TOKEN missing.
try:
    settings = _build_settings()
except Exception:  # pragma: no cover - surfaced to caller
    raise
