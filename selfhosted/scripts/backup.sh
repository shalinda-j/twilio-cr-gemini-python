#!/usr/bin/env bash
# Backs up the dashboard SQLite database. Add to cron for daily backups:
#   0 2 * * * bash /root/twilio-cr-gemini-python/selfhosted/scripts/backup.sh
set -euo pipefail
cd "$(dirname "$0")/.."          # -> selfhosted/

STAMP=$(date +%Y%m%d-%H%M%S)
OUT="backups"; mkdir -p "$OUT"
DB="dashboard-data/dashboard.db"

if [ -f "$DB" ]; then
  cp "$DB" "$OUT/dashboard-$STAMP.db"
  ls -1t "$OUT"/dashboard-*.db | tail -n +15 | xargs -r rm   # keep last 14
  echo "✅ Backed up to $OUT/dashboard-$STAMP.db"
else
  echo "⚠️  $DB not found (using Postgres? back that up with pg_dump instead)."
fi
