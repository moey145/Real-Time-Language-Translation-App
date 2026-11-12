from __future__ import annotations

from fastapi.testclient import TestClient

from server.main import create_app

from .conftest import configure, receive_until


def types(events):
    return [e["type"] for e in events]


def test_config_endpoint_and_frontend(client):
    data = client.get("/api/config").json()
    codes = {lang["code"] for lang in data["languages"]}
    assert {"en", "es", "zh", "ar"} <= codes
    assert data["defaults"] == {"mode": "translate", "source": "auto", "target": "es", "lang_a": "en", "lang_b": "es"}

    page = client.get("/")
    assert page.status_code == 200
    assert "Live Translator" in page.text
    assert page.headers["x-content-type-options"] == "nosniff"
    for asset in ("/app.js", "/speech.js", "/styles.css"):
        assert client.get(asset).status_code == 200


def test_typed_text_is_translated(client, translator):
    with client.websocket_connect("/ws") as ws:
        assert ws.receive_json()["type"] == "ready"
        configure(ws, source="auto", target="fr")
        ws.send_json({"type": "text", "text": "  good morning  "})
        events = receive_until(ws, "translation.done")

    assert types(events) == ["utterance.start", "transcript.done", "translation.delta", "translation.done"]
    assert events[0]["kind"] == "text"
    assert events[-1] == {"type": "translation.done", "id": 1, "text": "[fr] good morning", "source": None, "target": "fr"}
    request = translator.requests[0]
    assert (request.text, request.source, request.target) == ("good morning", None, "fr")


def test_voice_phrase_carries_spoken_language(client, translator):
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        configure(ws, source="auto", target="en")
        ws.send_json({"type": "text", "text": "hola mundo", "spoken": "es"})
        events = receive_until(ws, "translation.done")

    assert events[0]["kind"] == "voice"
    assert events[1]["language"] == "es"
    assert (events[-1]["source"], events[-1]["target"]) == ("es", "en")
    assert translator.requests[0].source == "es"


def test_fixed_source_language_is_used_for_typed_text(client, translator):
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        configure(ws, source="de", target="en")
        ws.send_json({"type": "text", "text": "Guten Tag"})
        receive_until(ws, "translation.done")
    assert translator.requests[0].source == "de"


def test_conversation_mode_routes_by_spoken_language(client, translator):
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        configure(ws, mode="conversation", lang_a="en", lang_b="es")
        ws.send_json({"type": "text", "text": "hola", "spoken": "es"})
        done = receive_until(ws, "translation.done")[-1]
        ws.send_json({"type": "text", "text": "hello", "spoken": "en"})
        done2 = receive_until(ws, "translation.done")[-1]

    assert [(r.source, r.target, r.pair) for r in translator.requests] == [("es", "en", None), ("en", "es", None)]
    assert (done["source"], done["target"]) == ("es", "en")
    assert (done2["source"], done2["target"]) == ("en", "es")


def test_conversation_mode_lets_claude_decide_for_typed_text(client, translator):
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        configure(ws, mode="conversation", lang_a="en", lang_b="de")
        ws.send_json({"type": "text", "text": "Hello there"})
        receive_until(ws, "translation.done")
    assert translator.requests[0].pair == ("en", "de")


def test_same_source_and_target_skips_translation(client, translator):
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        configure(ws, source="es", target="es")
        ws.send_json({"type": "text", "text": "hola"})
        done = receive_until(ws, "translation.done")[-1]
    assert done["text"] == "hola"
    assert translator.requests == []


def test_history_is_sent_as_context_and_can_be_reset(client, translator):
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        for text in ("first", "second"):
            ws.send_json({"type": "text", "text": text})
            receive_until(ws, "translation.done")
        ws.send_json({"type": "reset"})
        receive_until(ws, "reset")
        ws.send_json({"type": "text", "text": "third"})
        receive_until(ws, "translation.done")

    contexts = [r.context for r in translator.requests]
    assert len(contexts[0]) == 0
    assert [t.source_text for t in contexts[1]] == ["first"]
    assert len(contexts[2]) == 0


def test_rejects_bad_input(client, translator):
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_bytes(b"\x00\x01")
        assert ws.receive_json()["message"] == "Unsupported message."
        ws.send_json({"type": "config", "config": {"target": "xx"}})
        assert ws.receive_json() == {"type": "error", "message": "Invalid settings."}
        ws.send_json({"type": "text", "text": "hi", "spoken": "klingon"})
        assert ws.receive_json()["message"] == "Unsupported language."
        ws.send_text("{oops")
        assert ws.receive_json()["message"] == "Malformed message."
        ws.send_json({"type": "text", "text": "a" * 2001})
        assert "limited to 2000" in ws.receive_json()["message"]
    assert translator.requests == []


def test_rate_limit(translator, settings):
    settings.max_requests_per_minute = 2
    with TestClient(create_app(settings, translator)) as client, client.websocket_connect("/ws") as ws:
        ws.receive_json()
        for _ in range(2):
            ws.send_json({"type": "text", "text": "hi"})
            receive_until(ws, "translation.done")
        ws.send_json({"type": "text", "text": "hi"})
        assert "Too many requests" in ws.receive_json()["message"]


def test_missing_key_is_explained_to_the_user(settings, monkeypatch, tmp_path):
    for var in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_PROFILE", "ANTHROPIC_CONFIG_DIR"):
        monkeypatch.delenv(var, raising=False)
    for var in ("HOME", "USERPROFILE", "XDG_CONFIG_HOME", "APPDATA"):
        monkeypatch.setenv(var, str(tmp_path))
    with TestClient(create_app(settings)) as client, client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "text", "text": "hi"})
        error = receive_until(ws, "error")[-1]
    assert "ANTHROPIC_API_KEY" in error["message"]


def test_context_is_restored_after_reconnect(client, translator):
    turns = [
        {"source_lang": "en", "source_text": f"line {i}", "target_lang": "es", "translated_text": f"línea {i}"}
        for i in range(10)
    ]
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        ws.send_json({"type": "history", "turns": turns})
        ws.send_json({"type": "text", "text": "next"})
        receive_until(ws, "translation.done")

    context = translator.requests[0].context
    assert [t.source_text for t in context] == [f"line {i}" for i in range(4, 10)]  # last CONTEXT_TURNS kept
    assert context[-1].translated_text == "línea 9"


def test_malformed_history_is_rejected(client, translator):
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        for bad in ("nope", [{"source_text": "x"}], [{"source_text": "x", "translated_text": "y", "target_lang": "xx"}]):
            ws.send_json({"type": "history", "turns": bad})
            assert ws.receive_json()["message"] == "Could not restore the conversation context."
        ws.send_json({"type": "text", "text": "hi"})
        receive_until(ws, "translation.done")
    assert translator.requests[0].context == ()
