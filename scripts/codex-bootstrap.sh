#!/usr/bin/env bash
# Opt-in development bootstrap. Default mode changes nothing.
set -euo pipefail
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

usage() {
  cat <<'TXT'
Afisha Codex bootstrap
  bash scripts/codex-bootstrap.sh              # only read-only preflight
  bash scripts/codex-bootstrap.sh --deps       # install backend/frontend dependencies
  bash scripts/codex-bootstrap.sh --gstack     # opt-in gstack clone for Codex

Never automatically creates admin credentials, runs migrations or deploys.
TXT
}

case "${1:-}" in
  "")
    bash "$ROOT/scripts/codex-preflight.sh"
    usage
    ;;
  --deps)
    command -v python3 >/dev/null || { echo 'Python 3 is missing'; exit 1; }
    command -v npm >/dev/null || { echo 'npm is missing'; exit 1; }
    if [ ! -d "$ROOT/backend/.venv" ]; then python3 -m venv "$ROOT/backend/.venv"; fi
    "$ROOT/backend/.venv/bin/python" -m pip install -r "$ROOT/backend/requirements-dev.txt"
    ( cd "$ROOT/frontend" && npm ci )
    echo 'Dependencies ready. Fill backend/.env manually before starting the API.'
    ;;
  --gstack)
    command -v git >/dev/null || { echo 'Git is missing'; exit 1; }
    command -v bun >/dev/null || { echo 'Bun is missing; install a supported version first'; exit 1; }
    echo 'gstack is third-party software. Installing modifies Codex skills under your home directory.'
    printf 'Проверь https://github.com/garrytan/gstack и введи INSTALL для продолжения: '
    read -r consent
    if [ "$consent" != INSTALL ]; then echo 'Installation cancelled.'; exit 1; fi
    if [ -e "$HOME/gstack" ]; then
      echo 'Existing ~/gstack found. Not overwriting or updating it.'
      echo 'Review the checkout, then run: cd ~/gstack && ./setup --host codex --no-team --no-browser'
      exit 0
    fi
    git clone --single-branch --depth 1 https://github.com/garrytan/gstack.git "$HOME/gstack"
    echo 'Review ~/gstack/setup before executing it. No installer executed automatically.'
    echo 'Then run: cd ~/gstack && ./setup --host codex --no-team --no-browser && ./setup --status'
    ;;
  -h|--help) usage ;;
  *) usage; exit 2 ;;
esac
