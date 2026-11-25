#!/usr/bin/env bash
# Backup of THIS stack only: PostgreSQL dump + uploads archive + alembic revision. Read-only for the stack.
# Usage: backup.sh [out-dir]   (default ./backups, mode 700; copy off-host afterwards)
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env.staging; set +a
C() { docker compose --env-file .env.staging -f docker-compose.staging.yml "$@"; }
out=${1:-./backups}/$(date -u +%Y%m%dT%H%M%SZ); umask 077; mkdir -p "$out"
C exec -T db pg_dump -U afisha -d afisha_staging --format=custom > "$out/db.dump"
C exec -T db psql -U afisha -d afisha_staging -tAc "select version_num from alembic_version" > "$out/alembic_revision.txt"
docker run --rm -v "${COMPOSE_PROJECT_NAME}_uploads:/data:ro" --entrypoint tar "$BACKEND_IMAGE" -C /data -cf - . > "$out/uploads.tar"
( cd "$out" && shasum -a 256 db.dump uploads.tar alembic_revision.txt > SHA256SUMS )
echo "backup: $out (revision $(cat "$out/alembic_revision.txt"))"
