#!/usr/bin/env bash
# Pull latest code and (re)start the whole stack. Run:  bash selfhosted/scripts/deploy.sh
set -euo pipefail
cd "$(dirname "$0")/.."          # -> selfhosted/

git pull --ff-only
docker compose up -d --build
docker compose ps
echo "✅ Deployed. Logs: docker compose logs -f aiserver"
