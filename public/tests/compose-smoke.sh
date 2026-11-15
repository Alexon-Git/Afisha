#!/usr/bin/env bash
# Disposable integration only. Never uses backend/.env or an existing DB volume.
set -euo pipefail
project_root="$(cd "$(dirname "$0")/../.." && pwd)"
test_dir="$(mktemp -d "${TMPDIR:-/tmp}/afisha-pr10.XXXXXX")"
project="afisha_pr10_$(date +%s)_$$"
volume="${project}_data"
mkdir "$test_dir/uploads"
chmod 777 "$test_dir/uploads" # Disposable mount; no user data.
umask 077
cat > "$test_dir/test.env" <<EOF
POSTGRES_PASSWORD=pr10-disposable-db-password
DATABASE_URL=postgresql://afisha:pr10-disposable-db-password@db:5432/afisha_db
SECRET_KEY=pr10-disposable-secret-key-not-for-production-123456789
ADMIN_PASSWORD=pr10-disposable-admin-password
POSTGRES_VOLUME_NAME=$volume
UPLOADS_PATH=$test_dir/uploads
BACKEND_UID=1000
BACKEND_GID=1000
POSTGRES_PORT=${PR10_TEST_DB_PORT:-58039}
BACKEND_PORT=${PR10_TEST_BACKEND_PORT:-58040}
PUBLIC_PORT=${PR10_TEST_PUBLIC_PORT:-53010}
EOF
compose=(docker compose --project-name "$project" --env-file "$test_dir/test.env"
  -f "$project_root/backend/docker-compose.yml" -f "$project_root/backend/docker-compose.public.yml")
cleanup() {
  "${compose[@]}" down --remove-orphans >/dev/null
  if docker volume inspect "$volume" >/dev/null 2>&1; then
    owner="$(docker volume inspect --format '{{index .Labels "com.docker.compose.project"}}' "$volume")"
    if [[ "$owner" == "$project" ]]; then docker volume rm "$volume" >/dev/null; fi
  fi
  rm -f "$test_dir/test.env"
  rmdir "$test_dir/uploads" "$test_dir"
}
trap cleanup EXIT
"${compose[@]}" config --quiet
"${compose[@]}" build backend public
"${compose[@]}" up --detach --wait --wait-timeout 180
"${compose[@]}" exec -T public node - <<'JS'
const assert = require('node:assert/strict');
(async () => {
  assert.equal(process.getuid(), 1000);
  for (const key of ['DATABASE_URL', 'SECRET_KEY', 'ADMIN_PASSWORD', 'POSTGRES_PASSWORD']) assert.equal(process.env[key], undefined);
  assert.equal(process.env.INTERNAL_API_URL, 'http://backend:8039');
  assert.deepEqual(await (await fetch(`${process.env.INTERNAL_API_URL}/health`)).json(), { status: 'healthy' });
  const events = await (await fetch(`${process.env.INTERNAL_API_URL}/events/`)).json();
  assert.equal(events.total_items, 0);
  const home = await fetch('http://127.0.0.1:3000');
  assert.equal(home.status, 200);
  assert.match(await home.text(), /Соединение с сервисом установлено/);
  assert.equal((await fetch('http://127.0.0.1:3000/health')).status, 200);
  console.log('PASS Compose: non-root, public → backend DNS, home/health/events, no DB credentials in public');
})().catch(error => { console.error(error); process.exit(1); });
JS
for service in db backend public; do
  container="$("${compose[@]}" ps -q "$service")"
  docker inspect "$container" | python3 -c '
import json,sys
c=json.load(sys.stdin)[0]
assert c["State"]["Health"]["Status"] == "healthy"
assert c["HostConfig"]["ReadonlyRootfs"] or c["Config"]["Image"] == "postgres:17"
for bindings in c["HostConfig"]["PortBindings"].values():
 for bind in bindings or []: assert bind["HostIp"] == "127.0.0.1"
print("PASS health and localhost bindings:",c["Name"])
'
done
"${compose[@]}" stop backend
"${compose[@]}" exec -T public node - <<'JS'
(async () => {
  const assert = require('node:assert/strict');
  const response = await fetch('http://127.0.0.1:3000');
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /Сервис временно недоступен/);
  assert.doesNotMatch(html, /backend:8039|INTERNAL_API_URL|Traceback/);
  assert.equal((await fetch('http://127.0.0.1:3000/health')).status, 200);
  console.log('PASS Compose backend outage: safe fallback and independent public liveness');
})().catch(error => { console.error(error); process.exit(1); });
JS
