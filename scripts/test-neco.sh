#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[[ -f .env ]] || { echo 'Run ./install.sh first.' >&2; exit 1; }
TOKEN_FILE="$(python3 -c 'from neco.config import Settings; print(Settings.from_env().token_file)')"
[[ -s "$TOKEN_FILE" ]] || { echo 'Run ./scripts/set-token.sh first.' >&2; exit 1; }
exec "$ROOT/neco/.venv/bin/python" -m neco.runtime --test
