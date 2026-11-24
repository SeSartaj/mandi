#!/usr/bin/env bash
# Docker development stack with live reload (no per-change image rebuilds).
# Re-exec under bash when invoked as `sh scripts/dev-docker.sh`.
if [ -z "${BASH_VERSION:-}" ]; then exec bash "$0" "$@"; fi
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
COMPOSE=(docker compose -f compose.yml -f compose.dev.yml)
BACKEND_URL="http://127.0.0.1:8000"
FRONTEND_URL="http://127.0.0.1:5174"

env_value() {
  sed -n "s/^$1=//p" .env 2>/dev/null | tail -1
}

backend_running() {
  curl -fsS --max-time 2 "$BACKEND_URL/api/health/" >/dev/null 2>&1
}

frontend_running() {
  curl -fsS --max-time 2 "$FRONTEND_URL/" >/dev/null 2>&1
}

central_healthy() {
  local id
  id="$("${COMPOSE[@]}" ps -q central-service 2>/dev/null || true)"
  [[ -n "$id" ]] || return 1
  [[ "$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{end}}' "$id" 2>/dev/null)" == healthy ]]
}

start() {
  local with_frontend=0 with_central=0
  for arg in "$@"; do
    case "$arg" in
      --with-frontend) with_frontend=1 ;;
      --with-central) with_central=1 ;;
      *) echo "Unknown option: $arg" >&2; exit 1 ;;
    esac
  done
  if backend_running && ! "${COMPOSE[@]}" ps --status running --services 2>/dev/null | grep -qx backend-blue; then
    echo "Port 8000 is served by something else (host dev stack?)."
    echo "Stop it first: scripts/dev-local.sh stop"
    exit 1
  fi
  local services=(mandi-db backend-blue)
  ((with_frontend)) && services+=(frontend)
  # central-service pulls its dependencies (database, secrets, pyxform, mail,
  # enketo/redis) and, through public-ca, the Caddy proxy.
  ((with_central)) && services+=(central-service central-web)
  local cmd=("${COMPOSE[@]}")
  ((with_frontend)) && cmd+=(--profile frontend)
  cmd+=(up -d "${services[@]}")
  # Compose builds an image only when the tag is missing; afterwards the
  # bind-mounted source reloads without rebuilding.
  "${cmd[@]}"
  for _ in {1..60}; do
    backend_running && break
    sleep 1
  done
  if ((with_frontend)); then
    for _ in {1..120}; do
      frontend_running && break
      sleep 1
    done
  fi
  if ((with_central)); then
    echo "Waiting for ODK Central to finish its first-run bootstrap..."
    for _ in {1..150}; do
      central_healthy && break
      sleep 2
    done
  fi
  status
  echo "Backend log: docker compose -f compose.yml -f compose.dev.yml logs -f backend-blue"
  echo "Frontend:    ${FRONTEND_URL} (host: npm --prefix mandi_frontend run dev)"
  if ((with_central)); then
    echo "Central:     $(env_value PUBLIC_COLLECTION_URL) (admin $(env_value ODK_ADMIN_EMAIL))"
    echo "Central log: docker compose -f compose.yml -f compose.dev.yml logs -f central-service"
    echo "Signed HTTPS: ./scripts/local-ca.sh"
  fi
}

stop() {
  "${COMPOSE[@]}" stop backend-blue mandi-init frontend \
    central-service central-web central-enketo central-pyxform central-mail \
    central-secrets central-redis-main central-redis-cache central-db proxy \
    >/dev/null 2>&1 || true
  "${COMPOSE[@]}" rm -f backend-blue mandi-init frontend central-service central-web \
    >/dev/null 2>&1 || true
  echo "Stopped Docker development services (database and media volumes kept)."
}

status() {
  printf 'Backend  %s: ' "$BACKEND_URL"
  backend_running && echo ok || echo down
  printf 'Frontend %s: ' "$FRONTEND_URL"
  frontend_running && echo ok || echo down
}

case "${1:-start}" in
  start) shift || true; start "$@" ;;
  stop) stop ;;
  status) status ;;
  logs)
    "${COMPOSE[@]}" logs -f --tail=100 backend-blue
    ;;
  migrate)
    "${COMPOSE[@]}" exec backend-blue python manage.py migrate
    ;;
  test)
    "${COMPOSE[@]}" exec backend-blue python manage.py test tests
    ;;
  shell)
    "${COMPOSE[@]}" exec backend-blue python manage.py shell
    ;;
  *)
    echo "Usage: scripts/dev-docker.sh [start [--with-frontend] [--with-central]|stop|status|logs|migrate|test|shell]" >&2
    exit 1
    ;;
esac
