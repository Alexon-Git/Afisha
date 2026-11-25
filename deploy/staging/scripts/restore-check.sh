#!/usr/bin/env bash
# Verify a backup on a THROWAWAY postgres:17 container + temp dir. Never touches the staging stack.
# Usage: restore-check.sh <backup-dir>
set -euo pipefail
dir=$(cd "${1:?backup dir}" && pwd); name=afisha_restore_check_$$
( cd "$dir" && shasum -a 256 -c SHA256SUMS )
trap 'docker rm -f "$name" >/dev/null 2>&1 || true' EXIT
docker run -d --name "$name" -e POSTGRES_PASSWORD=restore-check -e POSTGRES_USER=afisha -e POSTGRES_DB=restore_check postgres:17 >/dev/null
for _ in $(seq 40); do docker exec "$name" pg_isready -U afisha -d restore_check >/dev/null 2>&1 && break; sleep 1; done
docker exec -i "$name" pg_restore -U afisha -d restore_check --no-owner < "$dir/db.dump"
q() { docker exec "$name" psql -U afisha -d restore_check -tAc "$1"; }
echo "alembic: $(q 'select version_num from alembic_version') (backup says $(cat "$dir/alembic_revision.txt"))"
echo "events=$(q 'select count(*) from events') articles=$(q 'select count(*) from articles') organizers=$(q 'select count(*) from organizers')"
echo "uploads files: $(tar -tf "$dir/uploads.tar" | grep -c '\.\(png\|jpg\|webp\)$')"
echo "restore-check OK"
