# Voice Assistant Dashboard

A secure, mobile-responsive, real-time dashboard for the self-hosted voice assistant.
Login, watch calls happen **live**, read transcripts, and see usage stats.

```
Voice server  --(call events, server-to-server)-->  Dashboard API  --(WebSocket)-->  Browser
                                                          │
                                                       SQLite DB
```

## Features
A sidebar console to **manage everything**:
- 📊 **Overview** — active/today/total calls, total minutes, 7-day chart, live activity
- 📞 **Calls** — history + per-call transcript (turn by turn, with language)
- #️⃣ **Phone Numbers** — add/remove DIDs
- 🔌 **SIP Providers** — store trunk/carrier connections
- 🔊 **Voice & TTS** — pick TTS provider + per-language voices
- 📚 **Knowledge Base** — add dataset/FAQ entries
- ⚙️ **Settings** — company name, AI persona, API key, webhook URL

Plus: 🔐 JWT + bcrypt login · 🏢 company-scoped (multi-tenant) · 🟢 live WebSocket updates · 📱 fully responsive.

> Numbers, call history and the live feed are fully wired. Voice/persona/knowledge
> settings are stored now and consumed by the live voice path as that wiring lands.

## Tech
FastAPI · SQLAlchemy (SQLite default, Postgres-ready) · JWT auth · WebSocket ·
Tailwind + Alpine.js + Chart.js (all via CDN, no build step).

## Run locally
```bash
cd dashboard
cp .env.example .env          # set ADMIN_*, JWT_SECRET, INGEST_TOKEN
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```
Open http://localhost:8000 and log in with the `ADMIN_EMAIL` / `ADMIN_PASSWORD` you set.

## Run with Docker (alongside the voice server)
The `selfhosted/docker-compose.yml` already includes a `dashboard` service:
```bash
cd selfhosted
cp ../dashboard/.env.example ../dashboard/.env   # edit secrets
docker compose up --build -d
```
Dashboard → `http://YOUR_DROPLET_IP:8000`

## How calls reach the dashboard
The voice server posts events to `POST /api/internal/ingest`, protected by the shared
`INGEST_TOKEN`. Set these on the **voice server** (`selfhosted/.env`):
```
DASHBOARD_INGEST_URL="http://127.0.0.1:8000/api/internal/ingest"
INGEST_TOKEN="<same value as the dashboard>"
```
Events: `call_started`, `message` (each user/assistant turn), `call_ended`.

## Security notes
- Always set a long random `JWT_SECRET` and `INGEST_TOKEN`.
- Change `ADMIN_PASSWORD` immediately; it is only used to seed the first user.
- Put the dashboard behind HTTPS (e.g. Caddy/Nginx + Let's Encrypt) before going public.
- `/api/internal/ingest` is meant for localhost/server-to-server only — don't expose port 8000
  publicly without a reverse proxy + firewall.

## REST API (all `/api/*` except login require `Authorization: Bearer <token>`)
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/login` | email+password → JWT |
| GET | `/api/me` | current user + company |
| GET | `/api/stats` | counters + 7-day series |
| GET | `/api/calls` | recent calls (paginated) |
| GET | `/api/calls/{id}` | one call + transcript |
| GET | `/api/numbers` | company phone numbers |
| POST | `/api/internal/ingest` | (server-to-server) call events |
| WS | `/ws/live?token=…` | live event stream |

## Multi-tenant (DID → company)
- Admins can create companies (`POST /api/companies`) and assign phone numbers
  (`POST /api/numbers`, or the **Phone numbers** card in the UI).
- Telephony registers each inbound call to its DID's company via
  `POST /api/internal/route` (form: `call_uuid`, `did`, `caller`, `token`) before
  the AI starts, so each company sees only its own calls.
- Calls without a known DID (e.g. softphone tests) fall back to the first company.

## Roadmap (not in v1)
- User management UI, roles, audit log
- Editable per-company AI persona from the dashboard
- CSV export, search/filter, date ranges
