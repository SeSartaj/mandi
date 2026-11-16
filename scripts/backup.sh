#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname "$0")/common.sh"
umask 077
backup_dir="$ROOT/backups/$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir -p "$backup_dir"
dc exec -T mandi-db pg_dump -U mandi -d mandi -Fc > "$backup_dir/mandi.dump"
dc run --rm --no-deps --entrypoint tar backend-blue czf - -C /app/media . > "$backup_dir/media.tgz"
if [[ "${1:-}" != --mandi-only ]]; then
  dc exec -T central-db pg_dump -U odk -d odk -Fc > "$backup_dir/central.dump"
  dc run --rm --no-deps --entrypoint tar central-secrets czf - -C /etc/secrets . > "$backup_dir/central-secrets.tgz"
fi
cp "$ENV_FILE" "$backup_dir/mandi.env"
for state in active previous; do
  [[ ! -f "deploy/runtime/$state" ]] || cp "deploy/runtime/$state" "$backup_dir/$state"
done
echo "Backup: $backup_dir (copy it to off-server storage)."
