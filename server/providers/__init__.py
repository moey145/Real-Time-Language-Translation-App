"""Factory for the Claude-backed translator."""

from __future__ import annotations

from anthropic import AsyncAnthropic

from ..config import Settings
from .base import ProviderError, Translator
from .claude_translator import ClaudeTranslator


def build_translator(settings: Settings) -> Translator:
    # Without an explicit key the SDK still resolves ANTHROPIC_API_KEY or an `ant auth login` profile.
    key = settings.anthropic_api_key.get_secret_value() if settings.anthropic_api_key else None
    client = AsyncAnthropic(api_key=key) if key else AsyncAnthropic()
    return ClaudeTranslator(client, settings.claude_model, settings.claude_effort)


__all__ = ["ProviderError", "Translator", "build_translator"]
