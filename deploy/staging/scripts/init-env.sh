#!/usr/bin/env bash
# Create .env.staging with random secrets and a Basic Auth file. Refuses to overwrite.
# Usage: init-env.sh <sha> [gate-user]   Prints the generated gate/admin passwords once to the terminal.
set -euo pipefail
cd "$(dirname "$0")/.."
sha=${1:?commit sha}; user=${2:-tester}
[ -e .env.staging ] && { echo ".env.staging exists; not overwriting" >&2; exit 1; }
umask 077; mkdir -p secrets
r() { openssl rand -hex "$1"; }
gate=$(r 12); admin=$(r 12)
sed -e "s/REPLACE_WITH_COMMIT_SHA/$sha/" \
    -e "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$(r 24)/" \
    -e "s/^SECRET_KEY=.*/SECRET_KEY=$(r 32)/" \
    -e "s/^ADMIN_PASSWORD=.*/ADMIN_PASSWORD=$admin/" .env.staging.example > .env.staging
printf '%s:%s\n' "$user" "$(openssl passwd -apr1 "$gate")" > secrets/staging.htpasswd
echo "gate login: $user / $gate"; echo "admin login: staging-admin / $admin"
