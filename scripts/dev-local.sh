#!/usr/bin/env bash
# Start, stop, or inspect the SQLite + Vite development stack.
# Re-exec under bash when invoked as `sh scripts/dev-local.sh`.
if [ -z "${BASH_VERSION:-}" ]; then exec bash "$0" "$@"; fi
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_LOG="${BACKEND_LOG:-/tmp/mandi-backend.log}"
FRONTEND_LOG="${FRONTEND_LOG:-/tmp/mandi-frontend.log}"
VENV="${VENV:-$ROOT/.venv}"
BACKEND_URL="http://127.0.0.1:8000"
FRONTEND_URL="http://127.0.0.1:5174"

backend_running() {
  curl -fsS --max-time 2 "$BACKEND_URL/api/health/" >/dev/null 2>&1
}

frontend_running() {
  curl -fsS --max-time 2 "$FRONTEND_URL/" >/dev/null 2>&1
}

start() {
  if backend_running; then
    echo "Backend already running: $BACKEND_URL"
  else
    screen -dmS mandi-backend bash -lc "cd '$ROOT/mandi_backend' && exec '$VENV/bin/python' manage.py runserver 0.0.0.0:8000 >'$BACKEND_LOG' 2>&1"
    echo "Started backend: $BACKEND_URL (log: $BACKEND_LOG, screen: mandi-backend)"
  fi
  if frontend_running; then
    echo "Frontend already running: $FRONTEND_URL"
  else
    screen -dmS mandi-frontend bash -lc "cd '$ROOT/mandi_frontend' && exec npm run dev -- --host 0.0.0.0 >'$FRONTEND_LOG' 2>&1"
    echo "Started frontend: $FRONTEND_URL (log: $FRONTEND_LOG, screen: mandi-frontend)"
  fi
  for _ in {1..30}; do
    backend_running && frontend_running && break
    sleep 0.5
  done
  status
}

stop() {
  screen -S mandi-backend -X quit >/dev/null 2>&1 || true
  screen -S mandi-frontend -X quit >/dev/null 2>&1 || true
  pkill -f "/home/foodev/afda/mandi/.venv/bin/python manage.py runserver 0.0.0.0:8000" || true
  pkill -f "node /home/foodev/afda/mandi/mandi_frontend/node_modules/.bin/vite" || true
  echo "Stopped local development services."
}

status() {
  printf 'Backend  %s: ' "$BACKEND_URL"
  backend_running && echo ok || echo down
  printf 'Frontend %s: ' "$FRONTEND_URL"
  frontend_running && echo ok || echo down
}

case "${1:-start}" in
  start) start ;;
  stop) stop ;;
  restart) stop; start ;;
  status) status ;;
  *) echo "Usage: scripts/dev-local.sh [start|stop|restart|status]" >&2; exit 1 ;;
esac
