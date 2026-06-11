# Connecting a 3CX PBX to the AI assistant

3CX cannot run the AI itself (its APIs don't expose live call audio), so the
integration is a **SIP trunk between 3CX and this server** — the only method
that carries voice. Calls routed to that trunk are answered by the assistant.

```
ISP / phone lines → 3CX (PBX) ──SIP trunk──▶ this server (Asterisk) → AI → Gemini
```

## Mode 1 — 3CX registers to us (recommended, NAT-friendly)

### On this server
1. Dashboard → **SIP Providers** → Add:
   - Type: **3CX PBX**
   - Name: e.g. `Office3CX`
   - Username: e.g. `3cxtrunk` · Password: a strong password
   - Host: leave blank
2. Apply: `bash selfhosted/scripts/apply-trunks.sh`

### In the 3CX Admin Console
1. **SIP Trunks → Add SIP Trunk** (select *Generic SIP Trunk*).
2. Registrar / SIP server: `YOUR_DROPLET_IP` (port `5060`).
3. Type of authentication: **Register/Account based**, with the same
   username/password you set in the dashboard.
4. Codecs: keep **G.711 a-law / u-law** at the top.
5. Save. The trunk should show **Registered** (green).

Verify on the server:
```bash
docker compose exec asterisk asterisk -rx "pjsip show endpoints"   # pbxN = Available
```

## Mode 2 — IP-based (3CX has a static public IP)
1. Dashboard → SIP Providers → Add → Type **3CX PBX**, Host = the 3CX public IP,
   leave username/password blank → `bash selfhosted/scripts/apply-trunks.sh`.
2. In 3CX, create the Generic trunk **without registration**, pointing at
   `YOUR_DROPLET_IP:5060`.

## Routing calls from 3CX to the AI
Any number 3CX sends down the trunk reaches the assistant (the `_X.` dialplan
catches everything). Typical setups:
- **Outbound Rule**: e.g. prefix `9` → route to this trunk. Users dial `9` + anything
  (e.g. `91000`) and get the AI.
- **Inbound DID**: point a 3CX inbound rule's destination at the trunk so callers
  on a specific number reach the AI directly.
- **IVR option**: "press 4 for the assistant" → forward to a number routed via the trunk.

## Firewall
The 3CX machine must be able to reach this server:
- `5060/udp` (SIP) and `10000-10100/udp` (RTP) — open in `ufw` (scripts/firewall.sh)
  **and** any DigitalOcean Cloud Firewall.

## Troubleshooting
| Symptom | Check |
|---|---|
| Trunk won't register | username/password match dashboard entry · `apply-trunks.sh` run · UDP 5060 reachable |
| Call connects, no audio | RTP ports `10000-10100/udp` open both ways · codecs G.711 |
| 3CX shows registered but calls fail | `docker compose exec asterisk asterisk -rvvv` then `pjsip set logger on` and place a call |
| Wrong company in dashboard | add the dialed number under **Phone Numbers** for the right company |
