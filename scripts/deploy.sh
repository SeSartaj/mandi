#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname "$0")/common.sh"
exec 9>deploy/.deploy.lock
flock -n 9 || { echo 'Another deployment is running.' >&2; exit 1; }
with_central=0
for arg in "$@"; do
  case "$arg" in
    --with-central) with_central=1 ;;
    *) echo 'Usage: scripts/deploy.sh [--with-central]' >&2; exit 1 ;;
  esac
done
if [[ "${ENVIRONMENT:-local}" == production ]]; then
  for key in MANDI_DOMAIN ODK_DOMAIN SYSADMIN_EMAIL TLS_ISSUER ODK_ADMIN_EMAIL ODK_EMAIL MANDI_ADMIN_EMAIL; do
    [[ -n "${!key:-}" && "${!key}" != *example.* && "${!key}" != *localhost* && "${!key}" != internal ]] || { echo "Set production $key in .env" >&2; exit 1; }
  done
  [[ "${PUBLIC_COLLECTION_URL:-}" == https://* ]] || { echo 'PUBLIC_COLLECTION_URL must use https in production.' >&2; exit 1; }
  [[ -z "${LAN_HTTP_HOST:-}" ]] || { echo 'LAN_HTTP_HOST must be empty in production.' >&2; exit 1; }
fi
mkdir -p deploy/runtime/routes backups
[[ -f deploy/runtime/routes/mandi.caddy ]] || echo 'reverse_proxy web-blue:80' > deploy/runtime/routes/mandi.caddy
write_lan_route
dc config --quiet
export RELEASE="$(date -u +%Y%m%d%H%M%S)-$(git rev-parse --short HEAD)"
old_slot=''
[[ ! -f deploy/runtime/active ]] || read -r old_slot old_release < deploy/runtime/active
if [[ -z "$old_slot" && -n "$(dc ps --status running -q backend-blue)" ]]; then
  old_slot=blue
  old_release="${BLUE_RELEASE:-local}"
fi
if [[ -z "$old_slot" ]]; then
  export SLOT=blue BLUE_RELEASE="$RELEASE" GREEN_RELEASE="$RELEASE"
  # First installation starts the whole Compose project, including Central.
  ensure_central
  dc build --pull
  dc up -d --wait --wait-timeout 900
else
  export SLOT=blue
  [[ "$old_slot" != blue ]] || SLOT=green
  set_slot_release
  # Routine Mandi releases do not rebuild or restart Central. Upgrades are
  # explicit because they may need a maintenance window and a database upgrade.
  if [[ "$with_central" == 1 ]]; then
    ensure_central
    dc build --pull central-secrets central-service central-web central-enketo
    dc up -d --wait --wait-timeout 900 central-db central-secrets central-service central-web central-enketo \
      central-pyxform central-mail central-redis-main central-redis-cache public-ca
  fi
  dc build --pull "backend-$SLOT" "web-$SLOT"
  ./scripts/backup.sh --mandi-only
  dc run --rm --no-deps "backend-$SLOT" python manage.py check --deploy --fail-level ERROR
  dc run --rm --no-deps "backend-$SLOT" python manage.py migrate --noinput
  dc run --rm --no-deps "backend-$SLOT" python manage.py bootstrap_admin
  dc up -d --no-deps --wait --wait-timeout 240 "backend-$SLOT" "web-$SLOT"
fi
dc exec -T "web-$SLOT" wget -q -O /dev/null --header="Host: $MANDI_DOMAIN" http://127.0.0.1/api/health/
cp deploy/runtime/routes/mandi.caddy deploy/runtime/routes/mandi.previous
printf 'reverse_proxy web-%s:80\n' "$SLOT" > deploy/runtime/routes/mandi.next
mv deploy/runtime/routes/mandi.next deploy/runtime/routes/mandi.caddy
rollback_route() {
  cp deploy/runtime/routes/mandi.previous deploy/runtime/routes/mandi.caddy
  dc exec -T proxy caddy reload --config /etc/caddy/Caddyfile || true
}
if ! dc exec -T proxy caddy reload --config /etc/caddy/Caddyfile; then rollback_route; exit 1; fi
if [[ "${TLS_ISSUER:-internal}" == internal ]]; then ./scripts/local-ca.sh; fi
if ! public_check --fail --silent --show-error --retry 12 --retry-delay 2 --connect-timeout 5 --max-time 10 "$(public_url "$MANDI_DOMAIN")/api/health/"; then
  rollback_route; exit 1
fi
# Reuse the candidate backend image for the single worker.
if ! dc up -d --no-deps worker; then rollback_route; exit 1; fi
save_release
[[ -z "$old_slot" ]] || printf '%s %s\n' "$old_slot" "$old_release" > deploy/runtime/previous
printf '%s %s\n' "$SLOT" "$RELEASE" > deploy/runtime/active
echo "Deployed $RELEASE ($SLOT): $(public_url "$MANDI_DOMAIN")"
