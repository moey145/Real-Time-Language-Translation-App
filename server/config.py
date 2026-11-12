"""Application settings, loaded from environment variables or a local .env file."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    anthropic_api_key: SecretStr | None = None

    claude_model: str = "claude-haiku-5-5"
    claude_effort: Literal["low", "medium", "high", "xhigh", "max"] = "low"
    context_turns: int = 6  # previous exchanges sent to Claude for context

    max_text_chars: int = 2000
    max_requests_per_minute: int = 40


@lru_cache
def get_settings() -> Settings:
    return Settings()
