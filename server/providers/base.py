"""Translator interface shared by the pipeline and the Claude client."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

OnDelta = Callable[[str], Awaitable[None]]


class ProviderError(Exception):
    """An error that is safe to show to the user."""


@dataclass(frozen=True)
class Turn:
    """One finished exchange, kept as context for later translations."""

    source_lang: str | None
    source_text: str
    target_lang: str
    translated_text: str


@dataclass(frozen=True)
class TranslationRequest:
    text: str
    target: str | None = None  # known target language
    source: str | None = None  # known source language, or None to let the model infer it
    pair: tuple[str, str] | None = None  # conversation mode: translate into whichever of these the text is not in
    context: Sequence[Turn] = ()


@dataclass(frozen=True)
class Translation:
    text: str
    target: str
    source: str | None = None


class Translator(Protocol):
    async def translate(self, request: TranslationRequest, *, on_delta: OnDelta) -> Translation: ...
