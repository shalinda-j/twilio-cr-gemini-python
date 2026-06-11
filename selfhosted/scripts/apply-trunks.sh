#!/usr/bin/env bash
# Push the SIP providers you added in the dashboard to Asterisk and reload.
# Run on the droplet after adding/removing providers:
#   bash selfhosted/scripts/apply-trunks.sh
set -euo pipefail
cd "$(dirname "$0")/.."          # -> selfhosted/

python3 scripts/gen_trunks.py

if docker compose exec -T asterisk asterisk -rx "pjsip reload" 2>/dev/null; then
  echo "✅ Trunks applied and Asterisk reloaded."
else
  echo "⚠️  Generated config, but could not reload Asterisk automatically."
  echo "   Run: docker compose exec asterisk asterisk -rx \"pjsip reload\""
fi
echo "   Verify: docker compose exec asterisk asterisk -rx \"pjsip show registrations\""
