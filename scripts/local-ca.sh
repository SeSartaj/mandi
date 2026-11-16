#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname "$0")/common.sh"
[[ "${TLS_ISSUER:-internal}" == internal ]] || { echo 'Production uses public certificates; no local CA is needed.'; exit 0; }
mkdir -p deploy/runtime
for attempt in $(seq 1 30); do
  if dc cp proxy:/data/caddy/pki/authorities/local/root.crt deploy/runtime/local-ca.crt >/dev/null 2>&1; then
    chmod 644 deploy/runtime/local-ca.crt
    echo "Local CA: $ROOT/deploy/runtime/local-ca.crt"
    echo 'To trust it on Ubuntu:'
    echo "  sudo cp '$ROOT/deploy/runtime/local-ca.crt' /usr/local/share/ca-certificates/mandi-local.crt"
    echo '  sudo update-ca-certificates'
    echo 'Restart your browser. Firefox may require importing this CA under Settings → Certificates → Authorities.'
    exit 0
  fi
  sleep 1
done
echo 'Local CA is not ready. Start the stack and inspect docker compose logs proxy.' >&2
exit 1
