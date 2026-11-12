from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from server.config import Settings
from server.main import create_app
from server.providers.base import Translation


class FakeTranslator:
    def __init__(self) -> None:
        self.requests = []

    async def translate(self, request, *, on_delta):
        self.requests.append(request)
        if request.pair:
            source, target = request.pair
        else:
            source, target = request.source, request.target
        text = f"[{target}] {request.text}"
        await on_delta(text)
        return Translation(text=text, target=target, source=source)


@pytest.fixture
def translator():
    return FakeTranslator()


@pytest.fixture
def settings():
    return Settings(_env_file=None, anthropic_api_key=None, max_requests_per_minute=100)


@pytest.fixture
def client(translator, settings):
    with TestClient(create_app(settings, translator)) as c:
        yield c


def receive_until(ws, event_type: str, limit: int = 50) -> list[dict]:
    """Collect messages up to and including the first one of `event_type`."""
    events = []
    for _ in range(limit):
        msg = ws.receive_json()
        events.append(msg)
        if msg["type"] == event_type:
            return events
    raise AssertionError(f"never received {event_type}: {events}")


def configure(ws, **config) -> dict:
    ws.send_json({"type": "config", "config": config})
    return receive_until(ws, "config")[-1]["config"]
