#!/usr/bin/env bash
# Read-only checks: subnet overlap with existing Docker networks, port in use, project name collision.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env.staging; set +a
python3 - "$STAGING_INTERNAL_SUBNET" "$STAGING_NGINX_IP" <<'PY'
import ipaddress, json, subprocess, sys
mine = ipaddress.ip_network(sys.argv[1]); assert ipaddress.ip_address(sys.argv[2]) in mine
ids = subprocess.check_output(["docker", "network", "ls", "-q"], text=True).split()
for n in json.loads(subprocess.check_output(["docker", "network", "inspect", *ids], text=True)):
    for c in (n.get("IPAM") or {}).get("Config") or []:
        if "Subnet" in c and ipaddress.ip_network(c["Subnet"]).overlaps(mine):
            sys.exit(f"subnet overlaps network {n['Name']}")
PY
if docker ps -a --filter "label=com.docker.compose.project=$COMPOSE_PROJECT_NAME" -q | grep -q .; then
  echo "note: project $COMPOSE_PROJECT_NAME already exists (update path)"; fi
if lsof -nP -iTCP:"$STAGING_PORT" -sTCP:LISTEN >/dev/null 2>&1; then echo "port $STAGING_PORT busy" >&2; exit 1; fi
echo "preflight OK"
