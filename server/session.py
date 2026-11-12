"""Per-connection translation pipeline with conversation context."""

from __future__ import annotations

import logging
from collections import deque
from collections.abc import Awaitable, Callable
from typing import Any, Literal

from pydantic import BaseModel, field_validator

from . import languages
from .config import Settings
from .providers.base import ProviderError, Translation, TranslationRequest, Translator, Turn

log = logging.getLogger(__name__)

Send = Callable[[dict[str, Any]], Awaitable[None]]


def _check_code(value: str) -> str:
    if not languages.is_supported(value):
        raise ValueError(f"unsupported language: {value}")
    return value


class SessionConfig(BaseModel):
    mode: Literal["translate", "conversation"] = "translate"
    source: str = "auto"  # "auto" or a language code (translate mode)
    target: str = "es"  # translate mode
    lang_a: str = "en"  # conversation mode
    lang_b: str = "es"  # conversation mode

    @field_validator("source")
    @classmethod
    def _source(cls, value: str) -> str:
        return value if value == "auto" else _check_code(value)

    @field_validator("target", "lang_a", "lang_b")
    @classmethod
    def _codes(cls, value: str) -> str:
        return _check_code(value)


class TranslationSession:
    def __init__(self, translator: Translator, settings: Settings, send: Send) -> None:
        self._translator = translator
        self._send = send
        self._next_id = 0
        self.config = SessionConfig()
        self.history: deque[Turn] = deque(maxlen=max(settings.context_turns, 0))

    def new_id(self) -> int:
        self._next_id += 1
        return self._next_id

    def reset(self) -> None:
        self.history.clear()

    async def run(self, uid: int, text: str, cfg: SessionConfig, *, spoken: str | None = None) -> None:
        """Translate one phrase. `spoken` is the language the browser recognised speech in, if voice input."""
        try:
            await self._run(uid, text, cfg, spoken)
        except ProviderError as exc:
            await self._send({"type": "error", "id": uid, "message": str(exc)})
        except Exception:
            log.exception("phrase %s failed", uid)
            await self._send({"type": "error", "id": uid, "message": "Something went wrong. Please try again."})

    async def _run(self, uid: int, text: str, cfg: SessionConfig, spoken: str | None) -> None:
        await self._send({"type": "utterance.start", "id": uid, "kind": "voice" if spoken else "text"})
        source = spoken or (None if cfg.mode == "conversation" or cfg.source == "auto" else cfg.source)
        await self._send({"type": "transcript.done", "id": uid, "text": text, "language": source})

        request = self._route(text, source, cfg)
        if request.source and request.source == request.target:
            translation = Translation(text=text, target=request.target, source=request.source)
            await self._send({"type": "translation.delta", "id": uid, "delta": text})
        else:
            async def on_delta(delta: str) -> None:
                await self._send({"type": "translation.delta", "id": uid, "delta": delta})

            translation = await self._translator.translate(request, on_delta=on_delta)

        await self._send(
            {
                "type": "translation.done",
                "id": uid,
                "text": translation.text,
                "source": translation.source,
                "target": translation.target,
            }
        )
        if translation.text:
            self.history.append(Turn(translation.source, text, translation.target, translation.text))

    def _route(self, text: str, source: str | None, cfg: SessionConfig) -> TranslationRequest:
        context = tuple(self.history)
        if cfg.mode == "conversation":
            a, b = cfg.lang_a, cfg.lang_b
            if source in (a, b) and a != b:
                return TranslationRequest(text, target=b if source == a else a, source=source, context=context)
            return TranslationRequest(text, pair=(a, b), context=context)
        return TranslationRequest(text, target=cfg.target, source=source, context=context)
