#!/usr/bin/env bash
set -Eeuo pipefail
rm -f /tmp/mandi-central-ready
./start-odk.sh &
server_pid=$!
trap 'kill -TERM "$server_pid" 2>/dev/null || true; wait "$server_pid" || true; exit 143' TERM INT
if ! node /opt/mandi/bootstrap.mjs; then
  kill -TERM "$server_pid" 2>/dev/null || true
  wait "$server_pid" || true
  exit 1
fi
wait "$server_pid"
