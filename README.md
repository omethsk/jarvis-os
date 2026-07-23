# JARVIS OS

A custom Iron-Man-inspired AI kiosk desktop for the Raspberry Pi. Boots straight into a fullscreen, animated desktop UI backed by a local Flask API and multiple LLM-driven "agent" personas -- not just a chatbot, a full desktop environment with AI-assisted apps.

## Architecture

- **Display shell** (`main.py`) -- a GTK4 + WebKitGTK fullscreen window that loads `assets/desktop.html` as the desktop. Runs under `labwc` (a lightweight Wayland compositor).
- **Backend** (`server.py`) -- a Flask app on port 5000 serving both the static UI assets and a JSON API: chat, weather, calendar, system stats, wallpapers, dock configuration, native app launching, and scoped power actions.
- **AI logic** (`jarvis_ai.py`) -- LLM calls go to **Groq** (`llama-3.3-70b-versatile`) first, falling back to a curated list of free **OpenRouter** models if Groq is rate-limited or down. Includes persistent memory extraction, Wikipedia grounding for generated content, and image sourcing via Pexels (real photos) or Pollinations (AI-generated).

### Three AI personas (`AGENTS` in `jarvis_ai.py`)

| Agent | Role | Tied to |
|---|---|---|
| **EDITH** | System control, terse and authoritative | Files, Terminal, Settings |
| **JARVIS** | Everyday assistant, dry wit | Browser, Write, Deck, Calc, Wallpapers |
| **FRIDAY** | Creative studio persona | Image generation ("Studio") |

### AI-driven apps

The `/jarvis-ai` endpoint does not just return chat text -- it returns structured **actions** the frontend applies directly:

- **Docs** (`write.html`) -- insert/append/replace/new HTML into a rich-text editor
- **Deck** -- full structured slide decks (layouts, charts, images, speaker notes, color themes)
- **Calc** -- spreadsheet cell writes with formulas and formatting
- **Studio** -- AI image generation via Pollinations

## Deployment

Two systemd services:

- `jarvis-display.service` (system-level) -- runs the `labwc` compositor as the kiosk user
- `jarvis.service` (user-level) -- runs the Flask backend

Both `Restart=always`. Two additional watchdog timers add self-healing:

- `jarvis-wifi-watchdog.timer` -- pings the gateway every 2 minutes and reconnects/restarts NetworkManager on failure
- `jarvis-backend-watchdog.timer` -- checks `/ping` every 2 minutes and restarts the backend if unresponsive

A daily `jarvis-autocommit.timer` snapshots and pushes any local changes at 3:00 AM.

## Setup

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env   # fill in your own API keys
```

Required environment variables (see `server.py` / `jarvis_ai.py` for exact usage):

- `GROQ_API_KEY`, `OPENROUTER_API_KEY` -- at least one required for AI features
- `PEXELS_API_KEY` -- real stock photos for Deck slides (optional)
- `CALENDAR_ICAL_URL` -- real calendar events (optional, feature is a graceful no-op if unset)
- `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID` -- reserved for future voice features (not yet wired into any code)

## Known limitations

- Calendar integration does not expand recurring events (RRULE) -- only each event's own first occurrence is considered.
- There is a real, unresolved performance ceiling: `WebKitWebProcess` runs at roughly 60-90% of one CPU core continuously, confirmed via `strace` to be dominated by GPU-sync (`ioctl`/`futex`) overhead rather than actual page content. This appears to be a WebKitGTK/Mesa-driver/kernel-level issue on Raspberry Pi 5, not fixable via a simple config change -- animations, compositing mode, and GPU-layer hints were all tested and ruled out as the cause.
- `gpiozero`/`lgpio`/`spidev` are installed in the venv but unused -- no GPIO hardware is currently wired up.
