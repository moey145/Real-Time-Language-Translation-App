"""FastAPI app: static frontend, config endpoint and the translation WebSocket."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import deque
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from . import languages
from .config import Settings, get_settings
from .providers import Translator, build_translator
from .session import SessionConfig, TranslationSession

log = logging.getLogger(__name__)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
MAX_PENDING = 6


def create_app(settings: Settings | None = None, translator: Translator | None = None) -> FastAPI:
    settings = settings or get_settings()
    translator = translator or build_translator(settings)
    app = FastAPI(title="Live Translator", docs_url=None, redoc_url=None)

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "microphone=(self)")
        return response

    @app.get("/healthz")
    async def healthz() -> dict:
        return {"ok": True}

    @app.get("/api/config")
    async def config() -> dict:
        return {
            "languages": [{"code": l.code, "name": l.name, "native": l.native} for l in languages.LANGUAGES],
            "defaults": SessionConfig().model_dump(),
            "limits": {"max_text_chars": settings.max_text_chars},
        }

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket) -> None:
        await ws.accept()
        send_lock = asyncio.Lock()
        closed = False

        async def send(payload: dict) -> None:
            if closed:
                return
            async with send_lock:
                try:
                    await ws.send_text(json.dumps(payload, ensure_ascii=False))
                except Exception:  # the client went away mid-send; the receive loop will clean up
                    log.debug("dropped message to closed websocket")

        session = TranslationSession(translator, settings, send)
        queue: asyncio.Queue = asyncio.Queue(maxsize=MAX_PENDING)
        recent: deque[float] = deque()

        async def worker() -> None:
            while True:
                job = await queue.get()
                try:
                    await job()
                finally:
                    queue.task_done()

        def allow_request() -> bool:
            now = time.monotonic()
            while recent and now - recent[0] > 60:
                recent.popleft()
            if len(recent) >= settings.max_requests_per_minute:
                return False
            recent.append(now)
            return True

        async def enqueue(text: str, spoken: str | None) -> None:
            if not allow_request():
                await send({"type": "error", "message": "Too many requests. Slow down for a moment."})
                return
            if queue.full():
                await send({"type": "error", "message": "Still working on earlier phrases. Try again shortly."})
                return
            uid = session.new_id()
            cfg = session.config.model_copy()
            queue.put_nowait(lambda: session.run(uid, text, cfg, spoken=spoken))

        worker_task = asyncio.create_task(worker())
        await send({"type": "ready", "config": session.config.model_dump()})
        try:
            while True:
                message = await ws.receive()
                if message["type"] == "websocket.disconnect":
                    break
                if message.get("text") is None:
                    await send({"type": "error", "message": "Unsupported message."})
                    continue
                await handle_text_frame(message["text"], session, send, enqueue, settings)
        except WebSocketDisconnect:
            pass
        finally:
            closed = True
            worker_task.cancel()

    if WEB_DIR.is_dir():
        app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
    return app


async def handle_text_frame(raw: str, session: TranslationSession, send, enqueue, settings: Settings) -> None:
    try:
        msg = json.loads(raw)
        kind = msg.get("type")
    except (ValueError, AttributeError):
        await send({"type": "error", "message": "Malformed message."})
        return

    if kind == "config":
        try:
            session.config = SessionConfig.model_validate({**session.config.model_dump(), **msg.get("config", {})})
        except (ValidationError, TypeError):
            await send({"type": "error", "message": "Invalid settings."})
            return
        await send({"type": "config", "config": session.config.model_dump()})
    elif kind == "text":
        text = str(msg.get("text", "")).strip()
        spoken = msg.get("spoken")
        if not text:
            return
        if spoken is not None and not languages.is_supported(spoken):
            await send({"type": "error", "message": "Unsupported language."})
            return
        if len(text) > settings.max_text_chars:
            await send({"type": "error", "message": f"Text is limited to {settings.max_text_chars} characters."})
            return
        await enqueue(text, spoken)
    elif kind == "reset":
        session.reset()
        await send({"type": "reset"})
    elif kind == "ping":
        await send({"type": "pong"})
    else:
        await send({"type": "error", "message": "Unknown message type."})


logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
app = create_app()
