# Live Translator

Real-time voice and text translation in 58 languages, running on a single API key. Speak naturally: your words appear as you talk, and each phrase is translated with conversation context as soon as you pause, then read aloud.

- **Live voice input.** The browser's built-in speech recognition shows your words as you speak and sends each phrase when you pause. There are no record/stop steps.
- **Context-aware translation with Claude.** Recent exchanges are sent along, so pronouns, formality and terminology stay consistent. The translation streams in word by word.
- **Conversation mode.** Two people, two languages, one mic button each. Every phrase is translated for the other person and spoken aloud.
- **Spoken output** with your device's own voices, with adjustable speed.
- Typed input with automatic language detection, copy, replay, transcript export, light and dark themes, works on phones.
- **One key, low cost.** Only an Anthropic API key is needed; speech recognition and speech output are free, built into the browser.

## How it works

```
Browser                                        Server (FastAPI)
───────                                        ────────────────
mic → Web Speech API (live words) ─┐
                                   ├─ phrase ──WS──▶ Claude Haiku 5.5 (streamed,
typed text ────────────────────────┘                 with recent context)
                                                          │
cards update live ◀──────────── translation deltas ───────┘
   └─▶ read aloud with the device's speech synthesis
```

One WebSocket per browser tab carries settings, phrases and the streamed translations. Each connection keeps a short history for context; nothing is stored on disk.

| Piece | File |
|---|---|
| App, routes, WebSocket, limits | [server/main.py](server/main.py) |
| Per-connection pipeline and routing | [server/session.py](server/session.py) |
| Claude translation | [server/providers/claude_translator.py](server/providers/claude_translator.py) |
| Speech recognition helpers | [web/speech.js](web/speech.js) |
| Frontend | [web/](web/) (no build step) |

## Quick start

Requires Python 3.11+ and an [Anthropic API key](https://console.anthropic.com).

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # then add ANTHROPIC_API_KEY
uvicorn server.main:app --reload
```

Open http://localhost:8000 in **Chrome, Edge or Safari**. Firefox has no speech recognition, so it supports typing only. Browsers allow the microphone only on `localhost` or over HTTPS.

### Vercel

1. Import the GitHub repo at https://vercel.com/new. No build settings are needed: `pyproject.toml` points Vercel at `server.main:app`, and `.python-version` pins Python 3.12.
2. Under **Settings → Environment Variables**, add `ANTHROPIC_API_KEY`, then deploy (or redeploy).
3. Make sure **Fluid compute** is on (**Settings → Functions**). It's the default for new projects, and WebSockets need it.

Vercel closes each WebSocket when the function reaches its maximum duration (5 minutes on the Hobby plan). The page reconnects straight away, resends any phrase that was cut off, and restores the recent conversation, so this is invisible apart from a brief "Connecting" dot.

The app is public once deployed, so set a monthly spend limit for your key in the Anthropic Console.

### Docker

```bash
docker build -t live-translator .
docker run --env-file .env -p 8000:8000 live-translator
```

The image listens on `$PORT` (default 8000), so it runs as-is on Render, Railway, Fly.io, Cloud Run and similar hosts. Serve it over HTTPS so the microphone works.

## Configuration

Environment variables (or entries in `.env`):

| Variable | Default | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | | Required. |
| `CLAUDE_MODEL` | `claude-haiku-5-5` | `claude-sonnet-5-5` or `claude-opus-5-5` for higher quality at a higher cost. |
| `CLAUDE_EFFORT` | `low` | Higher effort adds latency; `low` suits short phrases. |
| `CONTEXT_TURNS` | `6` | Earlier exchanges sent as context. |
| `MAX_TEXT_CHARS` | `2000` | |
| `MAX_REQUESTS_PER_MINUTE` | `40` | Per connection. |

## Using it

- **Translate mode:** choose *From* and *To*. With *Detect language*, typed text is auto-detected, and the mic listens in your browser's language. To speak another language, pick it in *From*.
- **Conversation mode:** choose each person's language. Person A taps the filled mic, person B the outlined one.
- **Space** toggles the mic (when you're not typing). **Enter** sends typed text, **Shift+Enter** adds a new line.
- The mic pauses while a translation is read aloud, so the app doesn't translate its own voice.
- Voice quality depends on the voices installed on the device. Edge's "Natural" voices and Chrome's Google voices sound best.

**Privacy note:** in Chrome and Edge, speech recognition audio is processed by Google's or Microsoft's speech service. Safari can recognise speech on the device.

## Development

```bash
pip install -r requirements-dev.txt
pytest
```

The tests use a fake translator, so they need no key and make no network calls. GitHub Actions runs them on every push and pull request.

## Costs

Speech recognition and speech output are free. Each phrase makes one Claude Haiku 5.5 call: a few hundred input tokens (instructions plus recent context) and a short reply. At Haiku 5.5's list price of $0.10 / $0.50 per million input/output tokens, that is roughly 10–20 cents per 1,000 phrases (an estimate). Set `CONTEXT_TURNS` lower to trim it further. The per-connection rate limit protects a public deployment from runaway use. Check current prices at https://www.anthropic.com/pricing.

## Author

Mohamad Eldhaibi · [GitHub](https://github.com/moey145) · [LinkedIn](https://www.linkedin.com/in/mohamad-eldhaibi-8ba8a42b7) · [Website](https://www.mohamadeldhaibi.com)
