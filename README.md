# AI Voice Assistant — Twilio *or* Self-Hosted (Python + Gemini)

An AI voice assistant you can **call on the phone** and talk to naturally, powered by the
[Google Gemini API](https://ai.google.dev/). It speaks **English and Sinhala**.

This repo ships **two ways to run it**, plus a **real-time web dashboard**:

| | Telephony | Cost | Effort | Best for |
|---|---|---|---|---|
| **A. Twilio** (`main.py`) | Twilio + ConversationRelay | per-minute (managed) | minutes | getting started fast |
| **B. Self-hosted** (`selfhosted/`) | Asterisk + your SIP trunk | only the SIP trunk | more setup | low cost at volume, full control |
| **Dashboard** (`dashboard/`) | — | — | — | login, live calls, transcripts, stats |

---

## Repository layout

```
.
├── main.py                # Option A: Twilio ConversationRelay app (managed)
├── requirements.txt       # deps for the Twilio app
├── selfhosted/            # Option B: no-Twilio stack (Asterisk + Whisper + Gemini + TTS)
│   ├── app/               #   async AudioSocket server, VAD, STT, LLM, TTS, reporting
│   ├── asterisk/          #   pjsip / extensions / rtp configs (softphone + SIP trunk)
│   ├── Caddyfile          #   automatic HTTPS reverse proxy
│   ├── docker-compose.yml #   aiserver + asterisk + dashboard + caddy
│   └── README.md          #   full DigitalOcean + softphone + trunk guide
└── dashboard/             # Web dashboard (FastAPI + SQLite, JWT auth, live WebSocket)
    ├── backend/           #   API, auth, models, ingest, multi-tenant routing
    ├── frontend/          #   responsive UI (Tailwind + Alpine + Chart.js)
    └── README.md          #   dashboard setup + API reference
```

---

## Option A — Twilio (quickest)

Twilio handles the phone call, speech-to-text and text-to-speech; this app just wires in Gemini.

```
Caller → Twilio (STT/TTS) ⇄ /ws (this app) → Gemini → reply → Twilio speaks it
```

**Prerequisites:** Python 3.10+, a [Twilio account](https://twil.io/try-twilio) + voice number,
and a [Google AI API key](https://aistudio.google.com/).

```bash
pip install -r requirements.txt
cp .env.example .env          # set GOOGLE_API_KEY and NGROK_URL
ngrok http 8080               # expose your local server
python main.py
```

Then point your Twilio number's **"A CALL COMES IN"** webhook at
`https://<your-ngrok-domain>/twiml` and call the number.

> Want a Sri Lankan / non-Twilio number with this option? See **BYOC** (Bring Your Own
> Carrier) — connect your own SIP trunk into Twilio. Otherwise use Option B.

---

## Option B — Self-hosted (no Twilio)

Run the whole pipeline yourself, so the only per-minute cost is your SIP trunk.

```
Phone / Softphone ──SIP──▶ Asterisk ──AudioSocket──▶ Python
   Python: WebRTC VAD → Whisper STT (EN/SI) → Gemini → TTS → back to the caller
```

- **STT:** faster-whisper (multilingual: English + Sinhala)
- **LLM:** Gemini
- **TTS:** pluggable — Google Cloud TTS (natural Sinhala + English) or Piper (free, English)
- **Telephony:** Asterisk; test instantly with a free softphone, then attach a real number via SIP trunk

Quick start (on an Ubuntu droplet with Docker):

```bash
cd selfhosted
cp .env.example .env                              # Gemini key, secrets
cp ../dashboard/.env.example ../dashboard/.env    # dashboard secrets
docker compose up --build -d
```

Register a softphone (Zoiper/Linphone) to extension `1000` and call it — no real number
needed to test. **Full step-by-step guide:** [`selfhosted/README.md`](selfhosted/README.md).

---

## The Dashboard

A secure, mobile-responsive dashboard with **live, real-time** updates.

- 🔐 JWT + bcrypt login, **company-scoped** data (multi-tenant)
- 🟢 Live call feed + transcripts over WebSocket (no refresh)
- 📊 Stat cards, 7-day chart, recent-calls table, per-call transcript
- 📱 Modern responsive UI (Tailwind + Alpine + Chart.js, no build step)
- 📞 Manage phone numbers; each inbound DID is routed to its company

The self-hosted voice server reports `call_started` / `message` / `call_ended` events to the
dashboard's token-protected ingest endpoint. **Details + API reference:**
[`dashboard/README.md`](dashboard/README.md).

---

## Production wiring (self-hosted)

- **HTTPS:** a `caddy` service gives automatic Let's Encrypt TLS — set `DASHBOARD_DOMAIN`
  and point its DNS at the droplet (serves plain HTTP on `:80` when unset).
- **Real phone number:** uncomment the SIP **trunk** block in `selfhosted/asterisk/pjsip.conf`
  and add the provider's credentials; inbound DIDs route automatically.
- **Multi-tenant:** add each DID in the dashboard (assigned to a company); Asterisk maps every
  inbound call to the right company before the AI answers.

> ⚠️ Keep `INGEST_TOKEN` **identical** in `selfhosted/.env` and `dashboard/.env`, and use
> long random values for `JWT_SECRET` and `INGEST_TOKEN`.

---

## How to choose

- **Just trying it / lowest effort →** Option A (Twilio).
- **Lowest per-minute cost at volume, full control, Sri Lankan number via local SIP trunk →**
  Option B (self-hosted).
- **Either way**, run the dashboard for live monitoring and transcripts.

## Costs at a glance

- **Twilio:** ConversationRelay + voice + TTS, billed per minute (managed, no servers to run).
- **Self-hosted:** a droplet (fixed) + SIP trunk minutes (and Google TTS if you use Sinhala).
  Open-source STT/TTS are free; cost drops as call volume grows and the server cost amortizes.
