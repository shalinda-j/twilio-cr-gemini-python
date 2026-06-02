# Full deployment to a single DigitalOcean Droplet

Runs the **whole platform** — Asterisk + AI voice server + dashboard + HTTPS — on one Droplet.

## 0. What you need first
- A DigitalOcean account
- A **Gemini API key** — https://aistudio.google.com/app/apikey
- TTS works out of the box with **gtts** (free, English + Sinhala, no credentials).
  For best quality, optionally use **Google Cloud TTS** (a service-account JSON with the
  *Text-to-Speech API* enabled).
- (Optional, for real calls) a **SIP trunk + phone number** from a provider
- (Optional, for HTTPS) a **domain** you can point at the droplet

---

## 1. Create the Droplet
DigitalOcean → **Create → Droplets**
- Image: **Ubuntu 22.04 LTS**
- Plan: **4 GB RAM / 2 vCPU** (Whisper needs RAM; use 8 GB for many concurrent calls)
- Add your SSH key → Create → copy the **public IP**

## 2. Log in and install Docker
```bash
ssh root@YOUR_DROPLET_IP
curl -fsSL https://get.docker.com | sh
```

## 3. Get the code
```bash
git clone https://github.com/shalinda-j/twilio-cr-gemini-python.git
cd twilio-cr-gemini-python
git checkout claude/project-explanation-FZoN2
```

## 4. Generate config (creates both .env files with matching secrets)
```bash
bash selfhosted/scripts/setup-env.sh
```
It asks for your Gemini key, admin login, company name, domain and TTS choice,
then writes `selfhosted/.env` and `dashboard/.env` with an **identical INGEST_TOKEN**.

Default TTS is **gtts** — no key needed. For Google Cloud TTS (`TTS_PROVIDER=google`),
upload your key into the `secrets/` folder (from your laptop):
```bash
scp gcp-key.json root@YOUR_DROPLET_IP:~/twilio-cr-gemini-python/selfhosted/secrets/gcp-key.json
```

## 5. Firewall
```bash
bash selfhosted/scripts/firewall.sh
```
Opens 22, 80, 443, 5060/udp, 10000-10100/udp. Keeps 8000/8090 private.

## 6. Launch everything
```bash
cd selfhosted
docker compose up --build -d
docker compose logs -f aiserver        # wait for: AudioSocket server listening
```
Containers: `aiserver`, `asterisk`, `dashboard`, `caddy`.

## 7. Open the dashboard
- With a domain set: `https://your-domain` (Caddy gets a cert automatically)
- Without: `http://YOUR_DROPLET_IP` (Caddy serves :80)

Log in with the admin email/password from step 4.

## 8. Test the AI with a free softphone (no number needed)
Install **Zoiper**/**Linphone**, add an account:
`Username 1000` · `Password` (from `asterisk/pjsip.conf`) · `Host YOUR_DROPLET_IP` · UDP.
Once registered, **dial 1000** and talk. Watch it appear **live** in the dashboard. 🎉

## 9. Connect a real phone number (when ready)
1. `asterisk/pjsip.conf` → uncomment the **trunk** block, add provider creds.
2. Dashboard → **Phone numbers** → add your DID (assigned to a company).
3. `docker compose exec asterisk asterisk -rx "pjsip reload"`
4. Call your number.

## 10. Backups & updates
```bash
# daily DB backup via cron
crontab -e
0 2 * * * bash /root/twilio-cr-gemini-python/selfhosted/scripts/backup.sh

# deploy new code later
bash selfhosted/scripts/deploy.sh
```
Also enable **DigitalOcean weekly snapshots** for the droplet.

---

## Troubleshooting
| Symptom | Check |
|---|---|
| aiserver won't start | `docker compose logs aiserver` — usually a missing `GOOGLE_API_KEY` (or, only with `TTS_PROVIDER=google`, a missing `secrets/gcp-key.json`) |
| Softphone won't register | `docker compose exec asterisk asterisk -rx "pjsip show endpoints"` |
| No / one-way audio | firewall RTP ports `10000-10100/udp` |
| Calls not in dashboard | `INGEST_TOKEN` must match in both .env files; `docker compose logs dashboard` |
| HTTPS cert fails | domain's DNS A record must point at the droplet; ports 80/443 open |
