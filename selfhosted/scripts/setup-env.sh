#!/usr/bin/env bash
# Generates selfhosted/.env and dashboard/.env with matching secrets.
# Run once on the droplet:  bash selfhosted/scripts/setup-env.sh
set -euo pipefail

cd "$(dirname "$0")/.."          # -> selfhosted/
ROOT="$(pwd)"
DASH="$(cd "$ROOT/../dashboard" && pwd)"

gen() { openssl rand -hex 24; }

echo "== Voice assistant setup =="
read -rp "Gemini API key (GOOGLE_API_KEY): " GOOGLE_API_KEY
read -rp "Admin email [admin@example.com]: " ADMIN_EMAIL; ADMIN_EMAIL=${ADMIN_EMAIL:-admin@example.com}
read -rp "Admin password [auto]: " ADMIN_PASSWORD; ADMIN_PASSWORD=${ADMIN_PASSWORD:-$(gen)}
read -rp "Company name [My Company]: " COMPANY_NAME; COMPANY_NAME=${COMPANY_NAME:-My Company}
read -rp "Dashboard domain (blank = HTTP on :80): " DASHBOARD_DOMAIN
read -rp "TTS provider google/piper [google]: " TTS_PROVIDER; TTS_PROVIDER=${TTS_PROVIDER:-google}

# One shared secret used by BOTH services for the ingest channel.
INGEST_TOKEN=$(gen)
JWT_SECRET=$(gen)

cat > "$ROOT/.env" <<EOF
GOOGLE_API_KEY="$GOOGLE_API_KEY"
GEMINI_MODEL="gemini-2.5-flash"
WHISPER_MODEL="small"
WHISPER_DEVICE="cpu"
WHISPER_COMPUTE="int8"
TTS_PROVIDER="$TTS_PROVIDER"
TTS_VOICE_EN="en-US-Standard-C"
TTS_VOICE_SI="si-LK-Standard-A"
AUDIOSOCKET_PORT="8090"
SILENCE_MS_END="800"
MIN_SPEECH_MS="300"
DASHBOARD_INGEST_URL="http://127.0.0.1:8000/api/internal/ingest"
INGEST_TOKEN="$INGEST_TOKEN"
DASHBOARD_DOMAIN="$DASHBOARD_DOMAIN"
EOF

cat > "$DASH/.env" <<EOF
DATABASE_URL="sqlite:///./data/dashboard.db"
COMPANY_NAME="$COMPANY_NAME"
ADMIN_EMAIL="$ADMIN_EMAIL"
ADMIN_PASSWORD="$ADMIN_PASSWORD"
JWT_SECRET="$JWT_SECRET"
JWT_EXPIRE_HOURS="12"
INGEST_TOKEN="$INGEST_TOKEN"
EOF

echo
echo "✅ Wrote $ROOT/.env and $DASH/.env (INGEST_TOKEN matched in both)."
echo "   Dashboard login -> $ADMIN_EMAIL / $ADMIN_PASSWORD"
[ "$TTS_PROVIDER" = "google" ] && echo "   NOTE: place your Google Cloud key at selfhosted/gcp-key.json for Sinhala TTS."
