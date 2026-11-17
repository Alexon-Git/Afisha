#!/usr/bin/env bash
# All Docker operations, including cleanup, use the isolated runner.
set -euo pipefail
exec python3 -I "$(cd "$(dirname "$0")" && pwd)/compose_smoke.py" "$@"
