# Self-Hosted AI Voice Assistant (No Twilio)

A fully self-hosted alternative to the Twilio version. You run everything yourself,
so the only per-minute cost is your SIP trunk (and Sinhala TTS if you use Google).

```
 Phone / Softphone
        │  SIP
        ▼
   Asterisk (telephony)
        │  AudioSocket (raw audio over TCP)
        ▼
   Python server
     ├─ WebRTC VAD   (detects when caller stops talking)
     ├─ Whisper STT  (speech -> text, English + Sinhala)
     ├─ Gemini       (the brain)
     └─ TTS          (text -> speech: Google = both langs, Piper = free English)
        │
        ▼  audio back to Asterisk -> caller
```

## What you need

1. **A server** - DigitalOcean droplet, Ubuntu 22.04, **at least 2 vCPU / 4 GB RAM**
   (Whisper needs RAM). ~$24/mo. A 2 GB droplet works with `WHISPER_MODEL=base`.
2. **Gemini API key** - https://aistudio.google.com/app/apikey
3. **Google Cloud TTS** (for Sinhala) - a service-account JSON key with the
   *Cloud Text-to-Speech API* enabled. (Skip if you only need English + Piper.)
4. **A softphone** - Zoiper or Linphone (free) on your phone/laptop for testing.
5. *(Later)* a **SIP trunk + phone number** to take real calls.

---

## Step 1 - Create the DigitalOcean droplet

1. DigitalOcean → **Create → Droplets** → Ubuntu 22.04, 4 GB / 2 vCPU.
2. Add your SSH key, create, and note the **public IP**.
3. **Networking → Firewall** (or `ufw`), open these ports:
   - `22/tcp` (SSH)
   - `5060/udp` (SIP)
   - `10000-10100/udp` (RTP / voice media)

## Step 2 - Install Docker on the droplet

```bash
ssh root@YOUR_DROPLET_IP
curl -fsSL https://get.docker.com | sh
```

## Step 3 - Get the code onto the droplet

```bash
git clone https://github.com/shalinda-j/twilio-cr-gemini-python.git
cd twilio-cr-gemini-python/selfhosted
```

## Step 4 - Configure secrets

```bash
cp .env.example .env
nano .env          # paste your GOOGLE_API_KEY (Gemini)
```

If using Google TTS (Sinhala), upload your service-account key as `gcp-key.json`
into this `selfhosted/` folder. From your laptop:

```bash
scp ~/Downloads/gcp-key.json root@YOUR_DROPLET_IP:~/twilio-cr-gemini-python/selfhosted/gcp-key.json
```

> English-only & free? Set `TTS_PROVIDER=piper` in `.env`, add a Piper voice model,
> and you can skip the Google key. (Sinhala still needs Google for natural speech.)

**Change the softphone password** in `asterisk/pjsip.conf` (`1000-auth` section).

## Step 5 - Launch

```bash
docker compose up --build -d
docker compose logs -f aiserver
```

First boot downloads the Whisper model (a minute or two). Wait until you see:

```
✅ AudioSocket server listening on 0.0.0.0:8090
```

## Step 6 - Test with a softphone (no real number needed)

Install **Zoiper** (or Linphone) and add an account:

| Field      | Value                          |
|------------|--------------------------------|
| Username   | `1000`                         |
| Password   | (what you set in pjsip.conf)   |
| Domain/Host| `YOUR_DROPLET_IP`              |
| Transport  | UDP                            |

Once it shows **Registered**, dial **`1000`** and start talking. You should hear the
greeting, then the AI answers in English or Sinhala depending on how you speak. 🎉

## Step 7 - Connect a real phone number (SIP trunk)

1. Buy a **SIP trunk + DID (phone number)** from a provider (local +94 or international wholesale).
2. In `asterisk/pjsip.conf`, uncomment the **SIP TRUNK** block and fill in the
   provider's `server`, `username`, `password`.
3. Reload Asterisk: `docker compose exec asterisk asterisk -rx "pjsip reload"`.
4. Inbound calls arrive on the dialed DID and are routed by the `_X.` pattern in
   `extensions.conf` — no extra dialplan needed.
5. Add the DID in the dashboard (see multi-tenant below) so calls are attributed correctly.

## Step 8 - HTTPS for the dashboard (Caddy)

A `caddy` service is included for automatic Let's Encrypt TLS.
1. Point a domain's **DNS A record** at the droplet (e.g. `dash.example.com`).
2. Open ports **80/tcp and 443/tcp** in the firewall.
3. Set `DASHBOARD_DOMAIN=dash.example.com` in `selfhosted/.env`, then
   `docker compose up -d`. Visit `https://dash.example.com`.
   (Leave it unset to serve plain HTTP on `:80` for IP testing.)
4. Keep port `8000` closed to the public; let Caddy front it.

## Step 9 - Multi-tenant (one server, many companies)

Each inbound DID is mapped to a company:
1. Log in to the dashboard as admin → **Phone numbers** → add your DID (and assign a company).
2. When a call comes in, Asterisk POSTs the call → DID → company mapping to the
   dashboard (`/api/internal/route`) before connecting the AI, so each company
   only sees its own calls. Softphone test calls (ext 1000, no DID) fall back to
   the first company.

> Make sure `INGEST_TOKEN` is **identical** in `selfhosted/.env` and `dashboard/.env`.

---

## Troubleshooting

Open the Asterisk CLI:

```bash
docker compose exec asterisk asterisk -rvvv
```

- `pjsip show endpoints` - is endpoint 1000 there / is the softphone Registered?
- `module show like audiosocket` - confirms AudioSocket support is loaded.
- Watch `docker compose logs -f aiserver` while you talk - you should see
  `🎙️ User (...)` and `🗣️ Assistant (...)` lines.
- No audio / one-way audio → almost always a firewall issue on `10000-10100/udp`.

## Tuning cost vs quality

| Setting | Cheaper / lighter | Better quality |
|---|---|---|
| `WHISPER_MODEL` | `tiny` / `base` | `small` / `medium` |
| `TTS_PROVIDER` | `piper` (free, English) | `google` (both langs) |
| Droplet | 2 GB + `base` | 4 GB + `small`, or GPU |

## Notes & limitations (v1)

- **Turn-based**: the assistant listens, then speaks. No barge-in (interrupting mid-reply) yet.
- **Sinhala TTS** realistically needs Google Cloud TTS; open-source Sinhala voices are weak.
- The Asterisk container config is the part most likely to need a small tweak for your
  image/version — the CLI commands above are your friend.
