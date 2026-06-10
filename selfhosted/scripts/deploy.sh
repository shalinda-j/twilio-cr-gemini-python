#!/usr/bin/env bash
# Pull latest code and (re)start the whole stack. Run:  bash selfhosted/scripts/deploy.sh
set -euo pipefail
cd "$(dirname "$0")/.."          # -> selfhosted/

git pull --ff-only

# Make sure the generated-trunks include exists so Asterisk boots without warnings.
mkdir -p asterisk-generated
[ -f asterisk-generated/pjsip_trunks.conf ] || \
  echo "; no SIP providers yet - add them in the dashboard, then run apply-trunks.sh" \
  > asterisk-generated/pjsip_trunks.conf

docker compose up -d --build
docker compose ps
echo "✅ Deployed. Logs: docker compose logs -f aiserver"
