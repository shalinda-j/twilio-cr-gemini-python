#!/usr/bin/env bash
# Opens only the ports this stack needs. Run as root:  bash selfhosted/scripts/firewall.sh
set -euo pipefail

ufw allow 22/tcp                 # SSH
ufw allow 80/tcp                 # HTTP (Caddy / Let's Encrypt)
ufw allow 443/tcp                # HTTPS (dashboard)
ufw allow 5060/udp               # SIP signalling
ufw allow 10000:10100/udp        # RTP media (voice)
ufw --force enable
ufw status verbose

echo "✅ Firewall set. Ports 8000 (dashboard) and 8090 (audiosocket) stay private."
