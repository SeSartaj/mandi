#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname "$0")/common.sh"
exec 9>deploy/.deploy.lock
flock -n 9 || exit 1
[[ -f deploy/runtime/previous ]] || { echo 'No previous release.' >&2; exit 1; }
read -r SLOT RELEASE < deploy/runtime/previous
export SLOT RELEASE
set_slot_release
dc up -d --no-deps --wait --wait-timeout 180 "backend-$SLOT" "web-$SLOT"
dc exec -T "web-$SLOT" wget -q -O /dev/null --header="Host: $MANDI_DOMAIN" http://127.0.0.1/api/health/
cp deploy/runtime/routes/mandi.caddy deploy/runtime/routes/mandi.previous
printf 'reverse_proxy web-%s:80\n' "$SLOT" > deploy/runtime/routes/mandi.next
mv deploy/runtime/routes/mandi.next deploy/runtime/routes/mandi.caddy
if ! dc exec -T proxy caddy reload --config /etc/caddy/Caddyfile; then
  cp deploy/runtime/routes/mandi.previous deploy/runtime/routes/mandi.caddy
  dc exec -T proxy caddy reload --config /etc/caddy/Caddyfile || true
  exit 1
fi
if [[ "${TLS_ISSUER:-internal}" == internal ]]; then ./scripts/local-ca.sh; fi
if ! public_check --fail --silent --show-error "$(public_url "$MANDI_DOMAIN")/api/health/"; then
  cp deploy/runtime/routes/mandi.previous deploy/runtime/routes/mandi.caddy
  dc exec -T proxy caddy reload --config /etc/caddy/Caddyfile
  exit 1
fi
dc up -d --no-deps worker
# Older releases predate the registry command; pause that worker on rollback.
if dc run --rm --no-deps registry-worker python manage.py help sync_registries >/dev/null 2>&1; then
  dc up -d --no-deps registry-worker
else
  dc stop registry-worker
fi
save_release
cp deploy/runtime/active deploy/runtime/active.swap
cp deploy/runtime/previous deploy/runtime/active
mv deploy/runtime/active.swap deploy/runtime/previous
echo "Rolled back application traffic to $RELEASE. Database migrations remain applied."
