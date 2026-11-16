#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
ENV_FILE="${MANDI_ENV_FILE:-$ROOT/.env}"
[[ -f "$ENV_FILE" ]] || { echo 'Run ./scripts/setup.sh first.' >&2; exit 1; }
# Configuration is data, never shell source.
while IFS= read -r line; do
  [[ "$line" =~ ^[A-Z][A-Z0-9_]*= ]] || continue
  export "$line"
done < "$ENV_FILE"
# Defaults let an older .env keep working after these keys were introduced.
CENTRAL_VERSION="${CENTRAL_VERSION:-2026.3.1}"
CENTRAL_COMMIT="${CENTRAL_COMMIT:-7d6de621955c5bb6a68e098ca10c9cbb92285cdf}"
PUBLIC_COLLECTION_URL="${PUBLIC_COLLECTION_URL:-https://${ODK_DOMAIN:-collect.localhost}:${HTTPS_PORT:-8443}}"
LAN_HTTP_HOST="${LAN_HTTP_HOST:-}"
export PUBLIC_COLLECTION_URL LAN_HTTP_HOST
CENTRAL_DIR="$ROOT/deploy/runtime/central"
dc() { docker compose --project-directory "$ROOT" --env-file "$ENV_FILE" -f "$ROOT/compose.yml" "$@"; }
# Phones cannot trust Caddy's internal CA in ODK Collect, so an optional
# plain-HTTP LAN route is generated only when LAN_HTTP_HOST is set.
write_lan_route() {
  mkdir -p "$ROOT/deploy/runtime/routes"
  local file="$ROOT/deploy/runtime/routes/lan.caddy"
  if [[ -n "${LAN_HTTP_HOST:-}" ]]; then
    printf 'http://%s:%s {\n\treverse_proxy central-web:80 {\n\t\theader_up Host %s\n\t}\n}\n' \
      "$LAN_HTTP_HOST" "${HTTP_PORT:-8080}" "$LAN_HTTP_HOST" > "$file"
  else
    printf '# LAN HTTP access disabled.\n' > "$file"
  fi
}
# Central builds need its `server` submodule; the upstream Dockerfile also
# runs `git describe`, so keep the real checkout instead of a tarball.
ensure_central() {
  mkdir -p "$ROOT/deploy/runtime"
  if [[ ! -d "$CENTRAL_DIR/.git" ]]; then
    if [[ -e "$CENTRAL_DIR" ]]; then
      echo "$CENTRAL_DIR exists but is not a Git checkout. Move it away and retry." >&2
      return 1
    fi
    git clone --depth 1 --branch "v$CENTRAL_VERSION" \
      https://github.com/getodk/central.git "$CENTRAL_DIR"
  fi
  # A failed clone aborts here; the directory check keeps test doubles simple.
  [[ -d "$CENTRAL_DIR/.git" ]] || return 0
  local head
  head="$(git -C "$CENTRAL_DIR" rev-parse HEAD)"
  if [[ "$head" != "$CENTRAL_COMMIT" ]]; then
    if [[ -n "$(git -C "$CENTRAL_DIR" status --porcelain)" ]]; then
      echo "$CENTRAL_DIR has local changes; commit or move them before upgrading." >&2
      return 1
    fi
    echo "Fetching Central v$CENTRAL_VERSION ($CENTRAL_COMMIT)..."
    git -C "$CENTRAL_DIR" fetch --depth 1 origin "refs/tags/v$CENTRAL_VERSION"
    git -C "$CENTRAL_DIR" checkout --detach FETCH_HEAD
    head="$(git -C "$CENTRAL_DIR" rev-parse HEAD)"
    if [[ "$head" != "$CENTRAL_COMMIT" ]]; then
      echo "Central checkout is $head, expected $CENTRAL_COMMIT for v$CENTRAL_VERSION." >&2
      return 1
    fi
  fi
  if [[ ! -f "$CENTRAL_DIR/server/package.json" ]]; then
    git -C "$CENTRAL_DIR" submodule update --init --recursive
  fi
  [[ -f "$CENTRAL_DIR/server/package.json" ]] || {
    echo 'Central server submodule is missing; run git submodule update --init --recursive.' >&2
    return 1
  }
}
public_url() {
  if [[ "${HTTPS_PORT:-8443}" == 443 ]]; then printf 'https://%s' "$1";
  else printf 'https://%s:%s' "$1" "${HTTPS_PORT:-8443}"; fi
}
public_check() {
  if [[ "${TLS_ISSUER:-internal}" == internal ]]; then
    curl --cacert "$ROOT/deploy/runtime/local-ca.crt" "$@"
  else
    curl "$@"
  fi
}
set_slot_release() {
  if [[ "$SLOT" == blue ]]; then export BLUE_RELEASE="$RELEASE";
  else export GREEN_RELEASE="$RELEASE"; fi
}
save_release() {
  python3 "$ROOT/scripts/release-state.py" "$ENV_FILE" "$SLOT" "$RELEASE"
}
