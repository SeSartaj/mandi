#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
umask 077
mode="${1:---local}"
[[ "$mode" == --local || "$mode" == --production ]] || { echo 'Usage: scripts/setup.sh [--local|--production]' >&2; exit 1; }
if [[ ! -e .env ]]; then
  template=.env.example
  [[ "$mode" != --production ]] || template=.env.production.example
  python3 - "$template" <<'PY'
from pathlib import Path
import secrets
import sys
text = Path(sys.argv[1]).read_text()
for key in ('POSTGRES_PASSWORD', 'ODK_DB_PASSWORD', 'DJANGO_SECRET_KEY', 'ODK_PASSWORD', 'ODK_ADMIN_PASSWORD', 'MANDI_ADMIN_PASSWORD'):
    text = text.replace(key + '=\n', key + '=' + secrets.token_hex(32) + '\n')
Path('.env').write_text(text)
PY
else
  echo '.env already exists; preserving its settings and passwords.'
fi
mkdir -p deploy/runtime/routes backups
[[ -f deploy/runtime/routes/mandi.caddy ]] || printf 'reverse_proxy web-blue:80\n' > deploy/runtime/routes/mandi.caddy
source "$(dirname "$0")/common.sh"
write_lan_route
ensure_central
if [[ "$mode" == --production ]]; then
  echo 'Set your public domains and email addresses in .env, then run ./scripts/deploy.sh.'
else
  echo 'Run: ./scripts/deploy.sh'
  echo "Mandi: https://$MANDI_DOMAIN:$HTTPS_PORT  Central: $PUBLIC_COLLECTION_URL"
  [[ -z "$LAN_HTTP_HOST" ]] || echo "Phone/LAN Central: http://$LAN_HTTP_HOST:$HTTP_PORT"
  echo 'After startup, trust the local certificate with ./scripts/local-ca.sh.'
fi
